from unittest.mock import patch

from accounts.api.errors import StructuredHttpError
from accounts.tests.base import APITestCase
from communities.models import Community, CommunityMembership
from core.models import UserProfile
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from featureflags.registry import HUB_FLAG_KEYS
from profiles.models import CommunityProfile

from cities.membership_service import change_member
from cities.models import City, CityAuditEvent, CityMembership, CityRevision
from cities.schemas import CityCreate, CityUpdate, MemberUpdate
from cities.services import create_city, update_city


class HubData:
    @classmethod
    def setUpTestData(cls):
        password = make_password("StrongPass123!")
        cls.users = {}
        for role in (
            "resident",
            "representative",
            "manager",
            "moderator",
            "outsider",
        ):
            cls.users[role] = get_user_model().objects.create(
                username=role,
                email=f"{role}@example.local",
                password=password,
                is_staff=role == "moderator",
                is_superuser=role == "moderator",
            )
        cls.community = Community.objects.create(
            slug="itmocraft", name="ItmoCraft"
        )
        for user in cls.users.values():
            CommunityMembership.objects.create(
                user=user, community=cls.community, status="active"
            )
        cls.city = create_city(
            cls.users["moderator"],
            CityCreate(
                community_slug="itmocraft",
                slug="alpha",
                name="Alpha",
                short_description="Город у реки",
                manager_username="manager",
                status="active",
                location={
                    "world": "overworld",
                    "map_id": "joutak",
                    "x": 1240,
                    "z": -438,
                },
            ),
        )
        for role in ("resident", "representative"):
            CityMembership.objects.create(
                city=cls.city, user=cls.users[role], status="active", role=role
            )


class CityServiceTests(HubData, TestCase):
    def test_atomic_create_and_audit(self):
        self.assertEqual(
            self.city.memberships.filter(role="manager").count(), 1
        )
        self.assertEqual(self.city.revisions.count(), 1)
        self.assertEqual(self.city.audit_events.count(), 2)

    def test_representative_edits_content_but_not_location(self):
        update_city(
            self.users["representative"],
            "alpha",
            CityUpdate(version=1, description="Новый текст"),
        )
        self.assertEqual(
            CityRevision.objects.get(version=2).content["description"],
            "Новый текст",
        )
        with self.assertRaises(StructuredHttpError) as raised:
            update_city(
                self.users["representative"],
                "alpha",
                CityUpdate(version=2, location=None),
            )
        self.assertEqual(raised.exception.status_code, 403)

    def test_stale_edit_does_not_overwrite_or_audit(self):
        update_city(
            self.users["manager"],
            "alpha",
            CityUpdate(version=1, description="first"),
        )
        events = CityAuditEvent.objects.count()
        with self.assertRaises(StructuredHttpError):
            update_city(
                self.users["manager"],
                "alpha",
                CityUpdate(version=1, description="stale"),
            )
        self.city.refresh_from_db()
        self.assertEqual(self.city.description, "first")
        self.assertEqual(CityAuditEvent.objects.count(), events)

    def test_last_manager_and_explicit_moderator_override(self):
        member = self.city.memberships.get(role="manager")
        with self.assertRaises(StructuredHttpError) as raised:
            change_member(
                self.users["moderator"],
                "alpha",
                member.pk,
                MemberUpdate(role="resident"),
            )
        self.assertEqual(
            raised.exception.payload["error_code"], "CITY_LAST_MANAGER"
        )
        change_member(
            self.users["moderator"],
            "alpha",
            member.pk,
            MemberUpdate(
                role="resident",
                override_reason="Временное управление платформой",
            ),
        )
        self.assertTrue(
            CityAuditEvent.objects.first().metadata["override_reason"]
        )

    def test_manager_cannot_promote_or_modify_manager(self):
        member = self.city.memberships.get(role="resident")
        with self.assertRaises(StructuredHttpError):
            change_member(
                self.users["manager"],
                "alpha",
                member.pk,
                MemberUpdate(role="manager"),
            )
        change_member(
            self.users["manager"],
            "alpha",
            member.pk,
            MemberUpdate(role="representative", position="Дипломат"),
        )
        member.refresh_from_db()
        self.assertEqual(member.role, "representative")

    def test_account_deletion_blocks_last_manager_and_retains_audit(self):
        with self.assertRaises(StructuredHttpError), transaction.atomic():
            self.users["manager"].delete()
        user = self.users["representative"]
        update_city(user, "alpha", CityUpdate(version=1, description="test"))
        user.delete()
        self.assertTrue(
            CityRevision.objects.filter(version=2, actor=None).exists()
        )
        self.assertTrue(
            CityAuditEvent.objects.filter(
                action="CITY_UPDATED", actor=None
            ).exists()
        )

    def test_database_rejects_duplicate_membership_and_partial_location(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            CityMembership.objects.create(
                city=self.city, user=self.users["manager"]
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            City.objects.filter(pk=self.city.pk).update(z=None)

    def test_failed_content_update_rolls_back_audit(self):
        events = CityAuditEvent.objects.count()
        with self.assertRaises(StructuredHttpError):
            update_city(
                self.users["manager"],
                "alpha",
                CityUpdate(
                    version=1,
                    location={
                        "world": "world",
                        "x": 0,
                        "z": 0,
                        "map_id": "unknown",
                    },
                ),
            )
        self.city.refresh_from_db()
        self.assertEqual(self.city.version, 1)
        self.assertEqual(CityAuditEvent.objects.count(), events)

    def test_seed_is_idempotent_and_preserves_edits(self):
        call_command("seed_itmocraft_community", verbosity=0)
        call_command("seed_itmocraft_community", verbosity=0)
        self.assertEqual(Community.objects.filter(slug="itmocraft").count(), 1)


class CityAPITests(HubData, APITestCase):
    def setUp(self):
        super().setUp()
        self.flags = patch(
            "communities.access.flags_for",
            return_value=dict.fromkeys(HUB_FLAG_KEYS, True),
        )
        self.flags.start()
        self.addCleanup(self.flags.stop)

    def headers(self, role):
        response = self.login(email=self.users[role].email)
        self.assertEqual(response.status_code, 200, response.content)
        return self.auth_headers(self.session_token(response))

    def test_guest_catalog_detail_map_and_hidden_cities(self):
        response = self.client.get("/api/cities")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["total"], 1)
        self.assertIsNone(response.json()["items"][0]["leader"])
        detail = self.client.get("/api/cities/alpha").json()
        self.assertEqual(
            response.json()["items"][0]["map_url"],
            detail["location"]["map_url"],
        )
        self.assertEqual(
            detail["location"]["map_url"],
            "https://map.joutak.ru/#joutak:1240:0:-438:1500:0:0:0:1:flat",
        )
        self.assertFalse(detail["capabilities"]["edit"])
        City.objects.filter(pk=self.city.pk).update(status="draft")
        self.assertEqual(self.client.get("/api/cities/alpha").status_code, 404)
        self.assertEqual(self.client.get("/api/cities").json()["total"], 0)

    def test_auth_and_permissions_enforced(self):
        self.assertEqual(
            self.patch_json(
                "/cities/alpha", {"version": 1, "description": "x"}
            ).status_code,
            401,
        )
        response = self.patch_json(
            "/cities/alpha",
            {"version": 1, "description": "x"},
            **self.headers("resident"),
        )
        self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(
            response.json()["error_code"], "CITY_PERMISSION_DENIED"
        )

    def test_representative_allowed_and_escalation_rejected(self):
        headers = self.headers("representative")
        response = self.patch_json(
            "/cities/alpha",
            {"version": 1, "description": "## Город"},
            **headers,
        )
        self.assertEqual(response.status_code, 200, response.content)
        member = self.city.memberships.get(role="resident")
        response = self.patch_json(
            f"/cities/alpha/members/{member.pk}",
            {"role": "PLATFORM_ADMIN"},
            **headers,
        )
        self.assertEqual(response.status_code, 422)

    def test_idor_and_contact_url_validation(self):
        other = City.objects.create(
            community=self.community,
            slug="beta",
            name="Beta",
            short_description="Beta",
        )
        member = CityMembership.objects.create(
            city=other, user=self.users["resident"], status="active"
        )
        headers = self.headers("manager")
        response = self.patch_json(
            f"/cities/alpha/members/{member.pk}",
            {"role": "representative"},
            **headers,
        )
        self.assertEqual(response.status_code, 404)
        response = self.patch_json(
            "/cities/alpha",
            {
                "version": 1,
                "contacts": [
                    {
                        "type": "website",
                        "label": "Bad",
                        "url": "javascript:alert(1)",
                    }
                ],
            },
            **headers,
        )
        self.assertEqual(response.status_code, 422)

    def test_public_profile_never_contains_private_legacy_fields(self):
        user = self.users["representative"]
        UserProfile.objects.create(
            user=user,
            itmo_isu="123456",
            minecraft_nick="PrivateNick",
            vk_username="private_vk",
        )
        CommunityProfile.objects.create(
            user=user,
            visibility="public",
            display_name="Публичное имя",
            minecraft_visibility="private",
        )
        response = self.client.get("/api/profiles/public/representative")
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        for field in (
            "email",
            "itmo_isu",
            "minecraft_nick",
            "vk_url",
            "is_staff",
            "id",
        ):
            self.assertNotIn(field, data)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(
            self.client.get("/api/profiles/public/resident").status_code, 404
        )

    def test_community_visibility_requires_shared_membership(self):
        user = self.users["representative"]
        CommunityProfile.objects.create(user=user, visibility="community")
        self.assertEqual(
            self.client.get("/api/profiles/public/representative").status_code,
            404,
        )
        response = self.client.get(
            "/api/profiles/public/representative", **self.headers("resident")
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_flags_gate_direct_api(self):
        with patch("communities.access.flags_for", return_value={}):
            self.assertEqual(self.client.get("/api/cities").status_code, 404)

    def test_account_delete_contract_blocks_last_manager(self):
        response = self.post_json(
            "/account/delete",
            {"current_password": self.default_password},
            **self.headers("manager"),
        )
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(response.json()["error_code"], "CITY_LAST_MANAGER")

    def test_self_profile_and_membership_privacy_updates(self):
        headers = self.headers("resident")
        response = self.client.get("/api/profiles/me", **headers)
        self.assertEqual(response.status_code, 200, response.content)
        profile = response.json()
        self.assertEqual(profile["visibility"], "private")
        payload = {
            key: profile[key]
            for key in (
                "version",
                "display_name",
                "bio",
                "visibility",
                "minecraft_visibility",
                "social_visibility",
                "itmo_visibility",
                "memberships_visibility",
            )
        }
        payload.update(visibility="public", memberships_visibility="public")
        response = self.patch_json("/profiles/me", payload, **headers)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            self.client.get("/api/profiles/public/resident").json()[
                "memberships"
            ]["cities"],
            [],
        )
        response = self.patch_json(
            "/cities/alpha/membership", {"visibility": "public"}, **headers
        )
        self.assertEqual(response.status_code, 200, response.content)
        cities = self.client.get("/api/profiles/public/resident").json()[
            "memberships"
        ]["cities"]
        self.assertEqual(cities[0]["slug"], "alpha")
        self.assertEqual(
            self.client.get("/api/account/memberships", **headers).status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/api/communities/itmocraft").status_code, 200
        )

    def test_legacy_account_without_memberships_can_edit_optional_profile(
        self,
    ):
        user = self.users["outsider"]
        CommunityMembership.objects.filter(user=user).delete()
        legacy = UserProfile.objects.create(
            user=user,
            minecraft_nick="LegacyPlayer",
            minecraft_has_license=True,
            vk_username="legacy_player",
            is_itmo_student=True,
            itmo_isu="123456",
        )
        headers = self.headers("outsider")
        before = self.client.get("/api/account/status", **headers)
        self.assertEqual(before.status_code, 200)
        response = self.client.get("/api/profiles/me", **headers)
        self.assertEqual(response.status_code, 200, response.content)
        profile = response.json()
        empty = {"communities": [], "cities": []}
        self.assertEqual(profile["memberships"], empty)
        self.assertEqual(profile["visibility"], "private")
        self.assertEqual(
            self.client.get("/api/account/memberships", **headers).json(),
            empty,
        )
        payload = {
            key: profile[key]
            for key in (
                "version",
                "display_name",
                "bio",
                "visibility",
                "minecraft_visibility",
                "social_visibility",
                "itmo_visibility",
                "memberships_visibility",
            )
        }
        payload.update(display_name="Новое имя", bio="Необязательное поле")
        response = self.patch_json("/profiles/me", payload, **headers)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["display_name"], "Новое имя")
        self.assertEqual(
            self.client.get("/api/account/status", **headers).json(),
            before.json(),
        )
        legacy.refresh_from_db()
        self.assertEqual(legacy.itmo_isu, "123456")
        self.assertEqual(legacy.minecraft_nick, "LegacyPlayer")

    def test_invalid_filters_and_coordinates(self):
        for query in ("page=0", "page=no", "recruitment=invalid"):
            self.assertEqual(
                self.client.get(f"/api/cities?{query}").status_code, 422
            )
        headers = self.headers("manager")
        for x in (True, "120", 30000001):
            response = self.patch_json(
                "/cities/alpha",
                {"version": 1, "location": {"world": "world", "x": x, "z": 0}},
                **headers,
            )
            self.assertEqual(response.status_code, 422)

    def test_moderator_create_archive_and_history(self):
        headers = self.headers("moderator")
        payload = {
            "community_slug": "itmocraft",
            "slug": "beta",
            "name": "Beta",
            "short_description": "Beta",
            "manager_username": "manager",
            "status": "active",
        }
        response = self.post_json("/moderation/cities", payload, **headers)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            self.post_json(
                "/moderation/cities", payload, **headers
            ).status_code,
            409,
        )
        response = self.patch_json(
            "/cities/beta", {"version": 1, "status": "archived"}, **headers
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.client.get("/api/cities/beta").status_code, 404)
        history = self.client.get("/api/cities/beta/history", **headers)
        self.assertEqual(history.status_code, 200, history.content)
        self.assertEqual(len(history.json()["revisions"]), 2)
        own = self.client.get(
            "/api/account/memberships", **self.headers("manager")
        ).json()
        archived = next(c for c in own["cities"] if c["slug"] == "beta")
        self.assertEqual(archived["city_status"], "archived")
        self.assertFalse(archived["can_manage"])
        self.assertEqual(
            self.client.get(
                "/api/moderation/cities?status=archived", **headers
            ).json()["total"],
            1,
        )

    def test_moderation_flag_gates_existing_manager_demotion(self):
        headers = self.headers("moderator")
        flags = dict.fromkeys(HUB_FLAG_KEYS, True)
        flags["cities_moderation_ui"] = False
        with patch("communities.access.flags_for", return_value=flags):
            response = self.patch_json(
                "/cities/alpha/members/1", {"role": "resident"}, **headers
            )
        self.assertEqual(response.status_code, 404)

    def test_public_username_me_does_not_collide_with_self_endpoint(self):
        user = self.users["resident"]
        user.username = "me"
        user.save()
        CommunityProfile.objects.create(user=user, visibility="public")
        response = self.client.get("/api/profiles/public/me")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["username"], "me")
        self.assertEqual(self.client.get("/api/profiles/me").status_code, 401)

    def test_roster_lifecycle_and_conflicts_are_audited(self):
        headers = self.headers("manager")
        payload = {"username": "outsider"}
        invitation = self.post_json(
            "/cities/alpha/invitations", payload, **headers
        )
        self.assertEqual(invitation.status_code, 200, invitation.content)
        self.assertFalse(
            self.city.memberships.filter(user=self.users["outsider"]).exists()
        )
        self.assertEqual(
            self.post_json(
                "/cities/alpha/invitations", payload, **headers
            ).status_code,
            409,
        )
        accepted = self.post_json(
            f"/account/city-invitations/{invitation.json()['id']}",
            {"decision": "accept"},
            **self.headers("outsider"),
        )
        self.assertEqual(accepted.status_code, 200, accepted.content)
        member_id = self.city.memberships.get(user=self.users["outsider"]).pk
        changed = self.patch_json(
            f"/cities/alpha/members/{member_id}",
            {"role": "representative", "position": "Архитектор"},
            **headers,
        )
        self.assertEqual(changed.status_code, 200, changed.content)
        removed = self.delete_json(
            f"/cities/alpha/members/{member_id}", **headers
        )
        self.assertEqual(removed.status_code, 200, removed.content)
        member = CityMembership.objects.get(pk=member_id)
        self.assertEqual(member.status, "removed")
        self.assertIsNotNone(member.left_at)
        self.assertEqual(
            self.city.audit_events.filter(
                target_membership_id=member_id
            ).count(),
            3,
        )

    def test_cookie_auth_alone_cannot_mutate_city(self):
        self.client.force_login(self.users["manager"])
        response = self.patch_json(
            "/cities/alpha", {"version": 1, "description": "forged"}
        )
        self.assertEqual(response.status_code, 401, response.content)

    def test_recent_moderation_filter_and_private_operations(self):
        headers = self.headers("moderator")
        self.assertEqual(
            self.client.get(
                "/api/moderation/cities?recent_days=7", **headers
            ).json()["total"],
            1,
        )
        City.objects.filter(pk=self.city.pk).update(
            updated_at="2020-01-01T00:00:00Z"
        )
        self.assertEqual(
            self.client.get(
                "/api/moderation/cities?recent_days=7", **headers
            ).json()["total"],
            0,
        )
        headers = self.headers("resident")
        for path in (
            "/api/cities/alpha/history",
            "/api/cities/alpha/members",
            "/api/moderation/cities",
        ):
            self.assertEqual(self.client.get(path, **headers).status_code, 403)
