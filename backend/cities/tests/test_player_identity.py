from unittest.mock import patch

from accounts.tests.base import APITestCase
from communities.models import CommunityMembership
from core.models import UserProfile
from django.contrib.auth import get_user_model
from featureflags.registry import HUB_FLAG_KEYS
from profiles.models import CommunityProfile

from cities.invitation_api import invitation_list
from cities.invitations import pending_invitations
from cities.models import CityMembership
from cities.queries import members
from cities.tests.test_hub import HubData


class PlayerIdentityTests(HubData, APITestCase):
    def setUp(self):
        super().setUp()
        flags = patch(
            "communities.access.flags_for",
            return_value=dict.fromkeys(HUB_FLAG_KEYS, True),
        )
        flags.start()
        self.addCleanup(flags.stop)
        for role in ("resident", "outsider"):
            CommunityProfile.objects.create(
                user=self.users[role],
                visibility="public",
                minecraft_visibility="community",
                display_name="Личное имя",
                avatar_url="https://example.org/avatar.webp",
            )
            UserProfile.objects.create(
                user=self.users[role], minecraft_nick=f"{role.title()}Craft"
            )
        response = self.login(username="manager")
        self.assertEqual(response.status_code, 200)
        self.headers = self.auth_headers(self.session_token(response))

    def resident(self):
        response = self.client.get("/api/cities/alpha/members", **self.headers)
        self.assertEqual(response.status_code, 200)
        return next(
            m for m in response.json()["items"] if m["username"] == "resident"
        )

    def test_manager_roster_obeys_profile_and_nickname_visibility(self):
        result = self.resident()
        self.assertEqual(result["minecraft_nick"], "ResidentCraft")
        self.assertEqual(result["username"], "resident")
        self.assertNotIn("display_name", result)
        profile = CommunityProfile.objects.filter(user=self.users["resident"])
        profile.update(minecraft_visibility="private")
        self.assertIsNone(self.resident()["minecraft_nick"])
        profile.update(minecraft_visibility="public", visibility="private")
        result = self.resident()
        self.assertIsNone(result["minecraft_nick"])
        self.assertIsNone(result["avatar_url"])
        profile.update(minecraft_visibility="community", visibility="public")
        CommunityMembership.objects.filter(user=self.users["resident"]).update(
            status="suspended"
        )
        self.assertIsNone(self.resident()["minecraft_nick"])

    def test_invitation_uses_visible_nickname_and_retains_account_key(self):
        response = self.post_json(
            "/cities/alpha/invitations",
            {"username": "outsider"},
            **self.headers,
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["minecraft_nick"], "OutsiderCraft")
        self.assertEqual(response.json()["username"], "outsider")
        CommunityProfile.objects.filter(user=self.users["outsider"]).update(
            visibility="private"
        )
        response = self.client.get(
            "/api/cities/alpha/invitations", **self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["items"][0]["minecraft_nick"])
        with self.assertNumQueries(2):
            listed = invitation_list(
                pending_invitations().filter(city=self.city),
                1,
                self.users["manager"],
            )
        self.assertEqual(listed.total, 1)

    def test_roster_identity_has_no_per_member_queries(self):
        users = get_user_model().objects.bulk_create(
            [get_user_model()(username=f"roster_{i:02d}") for i in range(24)]
        )
        CommunityProfile.objects.bulk_create(
            [
                CommunityProfile(
                    user=user,
                    visibility="public",
                    minecraft_visibility="community",
                )
                for user in users
            ]
        )
        UserProfile.objects.bulk_create(
            [
                UserProfile(user=user, minecraft_nick=f"Craft{i:02d}")
                for i, user in enumerate(users)
            ]
        )
        CommunityMembership.objects.bulk_create(
            [
                CommunityMembership(
                    user=user, community=self.community, status="active"
                )
                for user in users
            ]
        )
        CityMembership.objects.bulk_create(
            [
                CityMembership(user=user, city=self.city, status="active")
                for user in users
            ]
        )
        actor = self.users["manager"]
        actor.has_perm("cities.moderate_city")
        with self.assertNumQueries(4):
            result = members(actor, "alpha", 1)
        self.assertEqual(result.total, 27)
        self.assertEqual(len(result.items), 24)
        self.assertTrue(
            all(
                member.minecraft_nick
                for member in result.items
                if member.username.startswith("roster_")
            )
        )
