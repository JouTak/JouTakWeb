from unittest.mock import patch

from accounts.tests.base import APITestCase
from core.models import UserProfile
from featureflags.registry import HUB_FLAG_KEYS

from profiles.models import CommunityProfile, ProfileContact


class ProfileEditingData:
    def setUp(self):
        super().setUp()
        flags = patch(
            "communities.access.flags_for",
            return_value=dict.fromkeys(HUB_FLAG_KEYS, True),
        )
        flags.start()
        self.addCleanup(flags.stop)
        self.owner = self.create_legacy_user(username="editor")
        self.profile = CommunityProfile.objects.create(
            user=self.owner, visibility="public", social_visibility="public"
        )
        login = self.login(username=self.owner.username)
        self.headers = self.auth_headers(self.session_token(login))


class ProfileEditingTests(ProfileEditingData, APITestCase):
    def test_old_full_snapshot_cannot_reopen_profile(self):
        fields = (
            "version",
            "display_name",
            "bio",
            "avatar_url",
            "visibility",
            "minecraft_visibility",
            "social_visibility",
            "itmo_visibility",
            "memberships_visibility",
            "connections_visibility",
        )
        current = self.client.get("/api/profiles/me", **self.headers).json()
        snapshot = {key: current.get(key, "") for key in fields}
        result = self.patch_json(
            "/profiles/me",
            {**snapshot, "visibility": "private"},
            **self.headers,
        )
        self.assertEqual(result.status_code, 200)
        stale = self.patch_json(
            "/profiles/me",
            {**snapshot, "bio": "Старый редактор"},
            **self.headers,
        )
        self.assertEqual(stale.status_code, 409)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.visibility, "private")

    def test_removed_explicit_vk_does_not_republish_legacy(self):
        UserProfile.objects.update_or_create(
            user=self.owner, defaults={"vk_username": "old_address"}
        )
        ProfileContact.objects.create(
            user=self.owner,
            type="vk",
            value="new_address",
            visibility="private",
        )
        response = self.patch_json(
            "/profiles/me/contacts",
            {"version": 1, "contacts": []},
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        public = self.client.get("/api/profiles/public/editor").json()
        self.assertNotIn("vk_url", public)
        self.assertEqual(public["contacts"], [])

    def test_partial_save_and_invalid_inputs(
        self,
    ):
        self.profile.avatar_url = "https://example.com/avatar.png"
        self.profile.save()
        response = self.patch_json(
            "/profiles/me", {"version": 1, "bio": "  Мосты  "}, **self.headers
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["bio"], "Мосты")
        self.assertEqual(response.json()["version"], 2)
        self.assertEqual(
            response.json()["avatar_url"], self.profile.avatar_url
        )
        self.assertEqual(response.json()["display_name"], "")
        for payload in (
            {"bio": "oops"},
            {"version": 2, "visibility": None},
            {"version": 2, "avatar_url": None},
            {"version": 2, "username": "hacked"},
        ):
            self.assertEqual(
                self.patch_json(
                    "/profiles/me", payload, **self.headers
                ).status_code,
                422,
            )

    def test_contacts_have_independent_version_and_preserve_legacy_until_saved(
        self,
    ):
        UserProfile.objects.update_or_create(
            user=self.owner, defaults={"vk_username": "old_address"}
        )
        current = self.client.get(
            "/api/profiles/me/contacts", **self.headers
        ).json()
        self.assertEqual(current["contacts"][0]["value"], "old_address")
        self.assertEqual(current["contacts"][0]["visibility"], "public")
        self.patch_json(
            "/profiles/me", {"version": 1, "bio": "Новое"}, **self.headers
        )
        response = self.patch_json(
            "/profiles/me/contacts",
            {
                "version": 1,
                "contacts": [
                    {
                        "type": "telegram",
                        "value": "https://t.me/editor",
                        "visibility": "private",
                    }
                ],
            },
            **self.headers,
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["contacts"][0]["value"], "editor")
        response = self.patch_json(
            "/profiles/me/contacts", current, **self.headers
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            list(ProfileContact.objects.values_list("type", flat=True)),
            ["telegram"],
        )
        self.assertEqual(
            UserProfile.objects.get(user=self.owner).vk_username, "old_address"
        )

    def test_game_data_changes_only_supplied_fields_and_detects_legacy_writer(
        self,
    ):
        UserProfile.objects.update_or_create(
            user=self.owner,
            defaults={
                "minecraft_nick": "OldCraft",
                "vk_username": "old_vk",
                "is_itmo_student": False,
            },
        )
        initial = self.client.get(
            "/api/profiles/me/game-data", **self.headers
        ).json()
        self.assertIs(initial["is_itmo_student"], False)
        changed = self.patch_json(
            "/profiles/me/game-data",
            {"version": initial["version"], "minecraft_nick": " NewCraft "},
            **self.headers,
        )
        self.assertEqual(changed.status_code, 200, changed.content)
        self.assertEqual(changed.json()["minecraft_nick"], "NewCraft")
        self.assertEqual(changed.json()["vk_username"], "old_vk")
        self.patch_json(
            "/account/profile",
            {"is_itmo_student": True, "itmo_isu": "123456"},
            **self.headers,
        )
        conflict = self.patch_json(
            "/profiles/me/game-data",
            {
                "version": changed.json()["version"],
                "minecraft_nick": "StaleCraft",
            },
            **self.headers,
        )
        self.assertEqual(conflict.status_code, 409)
        profile = UserProfile.objects.get(user=self.owner)
        self.assertEqual(profile.itmo_isu, "123456")
        self.assertEqual(profile.minecraft_nick, "NewCraft")
        self.assertEqual(
            self.client.get(
                "/api/profiles/public/editor", **self.headers
            ).json()["minecraft_nick"],
            "NewCraft",
        )
