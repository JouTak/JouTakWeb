from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from accounts.api.errors import StructuredHttpError
from accounts.tests.base import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from featureflags.registry import HUB_FLAG_KEYS
from PIL import Image
from profiles.media import store_image
from profiles.models import CommunityProfile
from pydantic import ValidationError

from cities.integrations.bluemap import location_from_url
from cities.invitations import invite, respond, revoke
from cities.models import CityInvitation, CityMembership
from cities.schemas import ContactWrite
from cities.tests.test_hub import HubData


class InvitationServiceTests(HubData, TestCase):
    def test_consent_and_replay_never_elevate_role(self):
        result = invite(self.users["manager"], "alpha", "outsider")
        self.assertFalse(
            CityMembership.objects.filter(
                city=self.city, user=self.users["outsider"]
            ).exists()
        )
        with self.assertRaises(StructuredHttpError):
            respond(self.users["manager"], result.id, "accept")
        respond(self.users["outsider"], result.id, "accept")
        member = self.city.memberships.get(user=self.users["outsider"])
        self.assertEqual(member.role, "resident")
        self.assertEqual(member.visibility, "community")
        with self.assertRaises(StructuredHttpError):
            respond(self.users["outsider"], result.id, "accept")
        self.assertEqual(
            self.city.audit_events.filter(
                action="CITY_INVITATION_ACCEPTED"
            ).count(),
            1,
        )

    def test_decline_revoke_expiry_and_archive(self):
        manager, recipient = self.users["manager"], self.users["outsider"]
        first = invite(manager, "alpha", "outsider")
        respond(recipient, first.id, "decline")
        second = invite(manager, "alpha", "outsider")
        revoke(manager, "alpha", second.id)
        with self.assertRaises(StructuredHttpError):
            respond(recipient, second.id, "accept")
        third = invite(manager, "alpha", "outsider")
        CityInvitation.objects.filter(pk=third.id).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        with self.assertRaises(StructuredHttpError):
            respond(recipient, third.id, "accept")
        fourth = invite(manager, "alpha", "outsider")
        self.city.status = "archived"
        self.city.save()
        with self.assertRaises(StructuredHttpError):
            respond(recipient, fourth.id, "accept")
        self.assertFalse(self.city.memberships.filter(user=recipient).exists())

    def test_role_and_city_scope_are_enforced(self):
        for role in ("resident", "representative"):
            with self.assertRaises(StructuredHttpError):
                invite(self.users[role], "alpha", "outsider")
        invitation = invite(self.users["manager"], "alpha", "outsider")
        with self.assertRaises(StructuredHttpError):
            revoke(self.users["manager"], "another-city", invitation.id)
        self.assertEqual(
            CityInvitation.objects.get(pk=invitation.id).status, "pending"
        )


class HubRevisionAPITests(HubData, APITestCase):
    def setUp(self):
        super().setUp()
        flags = patch(
            "communities.access.flags_for",
            return_value=dict.fromkeys(HUB_FLAG_KEYS, True),
        )
        flags.start()
        self.addCleanup(flags.stop)

    def headers(self, role):
        response = self.login(email=self.users[role].email)
        self.assertEqual(response.status_code, 200, response.content)
        return self.auth_headers(self.session_token(response))

    def test_invitation_contract_and_legacy_add_cannot_bypass_consent(self):
        manager = self.headers("manager")
        self.assertEqual(
            self.post_json(
                "/cities/alpha/members", {"username": "outsider"}, **manager
            ).status_code,
            409,
        )
        self.assertEqual(
            self.post_json(
                "/cities/alpha/invitations",
                {"username": "outsider", "role": "manager"},
                **manager,
            ).status_code,
            422,
        )
        response = self.post_json(
            "/cities/alpha/invitations", {"username": "outsider"}, **manager
        )
        self.assertEqual(response.status_code, 200, response.content)
        recipient = self.headers("outsider")
        self.assertEqual(
            self.client.get(
                "/api/account/city-invitations", **recipient
            ).json()["total"],
            1,
        )
        self.assertEqual(
            self.client.get("/api/account/city-invitations", **manager).json()[
                "total"
            ],
            0,
        )
        self.assertEqual(
            self.post_json(
                f"/account/city-invitations/{response.json()['id']}",
                {"decision": "accept"},
                **manager,
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get("/api/account/city-invitations").status_code, 401
        )

    def test_residents_list_respects_both_privacy_layers(self):
        user = self.users["resident"]
        profile = CommunityProfile.objects.create(
            user=user, visibility="public", memberships_visibility="public"
        )
        membership = self.city.memberships.get(user=user)
        membership.visibility = "public"
        membership.save()
        response = self.client.get("/api/cities/alpha/residents")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["username"], "resident")
        self.assertNotIn("email", str(response.json()))
        profile.visibility = "private"
        profile.save()
        self.assertEqual(
            self.client.get("/api/cities/alpha/residents").json()["total"], 0
        )

    def test_map_and_upload_require_correct_scope(self):
        link = "https://map.joutak.ru/#joutak:1240:30:-438:1500:0:0:0:1:flat"
        self.assertEqual(
            self.post_json(
                "/cities/alpha/map-location",
                {"url": link},
                **self.headers("representative"),
            ).status_code,
            403,
        )

        response = self.post_json(
            "/cities/alpha/map-location",
            {"url": link},
            **self.headers("manager"),
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["x"], 1240)
        self.assertIsNone(response.json()["y"])
        self.assertEqual(
            self.client.post(
                "/api/cities/alpha/images",
                {
                    "file": SimpleUploadedFile(
                        "x.png", b"bad", content_type="image/png"
                    )
                },
                **self.headers("resident"),
            ).status_code,
            403,
        )

    def test_image_upload_contract_and_shared_quota(self):
        headers = self.headers("manager")
        original = BytesIO()
        Image.new("RGB", (12, 12), "blue").save(original, format="PNG")
        with TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            for endpoint in (
                "/api/profiles/images",
                "/api/cities/alpha/images",
            ):
                with self.subTest(endpoint=endpoint):
                    response = self.client.post(
                        endpoint,
                        {
                            "file": SimpleUploadedFile(
                                "logo.png",
                                original.getvalue(),
                                content_type="image/png",
                            )
                        },
                        **headers,
                    )
                    self.assertEqual(
                        response.status_code, 200, response.content
                    )
                    self.assertRegex(
                        response.json()["url"],
                        r"^/media/hub/[a-f0-9]{32}\.webp$",
                    )
            with patch("profiles.media.ratelimit_method", return_value=True):
                response = self.client.post(
                    "/api/profiles/images",
                    {
                        "file": SimpleUploadedFile(
                            "logo.png",
                            original.getvalue(),
                            content_type="image/png",
                        )
                    },
                    **headers,
                )
                self.assertEqual(response.status_code, 429, response.content)
                self.assertEqual(
                    response.json()["error_code"], "IMAGE_RATE_LIMITED"
                )


class ContentValidationTests(TestCase):
    def test_verified_map_link_parsing_and_attack_inputs(self):
        link = (
            "https://map.joutak.ru/#joutak:1240.3:0:-438.2:1500:0:0:0:1:flat"
        )
        self.assertEqual(location_from_url(link).z, -438)
        for value in (
            link.replace("map.joutak.ru", "map.joutak.ru.evil.test"),
            link.replace("1240.3", "NaN"),
            link.replace("1240.3", "1e99"),
            link.replace("joutak:", "unknown:"),
            link.replace("https:", "http:"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(StructuredHttpError),
            ):
                location_from_url(value)

    def test_provider_contacts(self):
        for kind, url in (
            ("discord", "https://discord.gg/test"),
            ("telegram", "https://t.me/city"),
            ("vk", "https://vk.com/city"),
        ):
            self.assertEqual(
                ContactWrite(type=kind, label="City", url=url).url, url
            )
        for kind, url in (
            ("website", "https://example.com"),
            ("discord", "https://evil.test/invite"),
            ("discord", "https://discord.com/channels/a"),
            ("telegram", "https://t.me.evil.test/city"),
        ):
            with self.subTest(url=url), self.assertRaises(ValidationError):
                ContactWrite(type=kind, label="City", url=url)

    def test_upload_reencodes_and_rejects_non_images(self):
        with TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            original = BytesIO()
            Image.new("RGB", (12, 12), "red").save(original, format="PNG")
            result = store_image(
                SimpleUploadedFile(
                    "../../unsafe.svg",
                    original.getvalue(),
                    content_type="image/png",
                )
            )
            self.assertRegex(result.url, r"^/media/hub/[a-f0-9]{32}\.webp$")
            with Image.open(
                root + result.url.removeprefix("/media")
            ) as output:
                self.assertEqual(output.format, "WEBP")
                self.assertFalse(output.getexif())
            for mime, data in (
                ("image/svg+xml", b"<svg/>"),
                ("image/png", b"<script/>"),
                ("image/png", b"x" * (3 * 1024 * 1024 + 1)),
            ):
                with (
                    self.subTest(mime=mime),
                    self.assertRaises(StructuredHttpError),
                ):
                    store_image(
                        SimpleUploadedFile("x", data, content_type=mime)
                    )
