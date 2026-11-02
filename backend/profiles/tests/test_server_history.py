from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import patch

from accounts.tests.base import APITestCase
from django.test import SimpleTestCase
from django.utils import timezone
from featureflags.registry import HUB_FLAG_KEYS

from profiles.models import CommunityProfile
from profiles.server_history import server_history


class ServerHistoryTests(SimpleTestCase):
    def test_russian_days_and_first_date(self):
        first = datetime(2026, 1, 1, tzinfo=dt_timezone.utc)
        profile = CommunityProfile(
            minecraft_first_joined_at=first, minecraft_visibility="public"
        )
        cases = {
            0: "дней",
            1: "день",
            2: "дня",
            4: "дня",
            5: "дней",
            11: "дней",
            12: "дней",
            14: "дней",
            21: "день",
            22: "дня",
            25: "дней",
            101: "день",
            111: "дней",
        }
        for days, noun in cases.items():
            with (
                self.subTest(days=days),
                timezone.override("UTC"),
                patch(
                    "django.utils.timezone.now",
                    return_value=first + timedelta(days=days),
                ),
            ):
                result = server_history(profile)
                self.assertEqual(result.days_text, f"{days} {noun}")
                self.assertEqual(result.first_joined_on, date(2026, 1, 1))

    def test_calendar_days_respect_timezone_and_future_dates(self):
        profile = CommunityProfile(
            minecraft_first_joined_at=datetime(
                2026, 1, 1, 20, 59, tzinfo=dt_timezone.utc
            ),
            minecraft_visibility="public",
        )
        with (
            timezone.override("Europe/Moscow"),
            patch(
                "django.utils.timezone.now",
                return_value=datetime(
                    2026, 1, 1, 21, 1, tzinfo=dt_timezone.utc
                ),
            ),
        ):
            self.assertEqual(server_history(profile).days_text, "1 день")
            profile.minecraft_first_joined_at += timedelta(days=2)
            self.assertIsNone(server_history(profile))

    def test_default_date_is_shared_baseline(self):
        profile = CommunityProfile(minecraft_visibility="public")
        with patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 2, 1, tzinfo=dt_timezone.utc),
        ):
            result = server_history(profile)
        self.assertEqual(result.first_joined_on, date(2026, 1, 1))
        self.assertEqual(result.days_text, "31 день")
        self.assertEqual(
            profile.minecraft_first_joined_at.date(), date(2026, 1, 1)
        )


class ServerHistoryAPITests(APITestCase):
    def setUp(self):
        super().setUp()
        flags = patch(
            "communities.access.flags_for",
            return_value=dict.fromkeys(HUB_FLAG_KEYS, True),
        )
        flags.start()
        self.addCleanup(flags.stop)
        self.user = self.create_legacy_user(username="first_login")
        self.profile = CommunityProfile.objects.create(
            user=self.user, visibility="public", minecraft_visibility="public"
        )

    def test_api_reports_default_then_imported_date_with_privacy(self):
        path = "/api/profiles/public/first_login"
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["server_history"]["first_joined_on"], "2026-01-01"
        )
        self.profile.minecraft_first_joined_at = datetime(
            2026, 2, 1, tzinfo=dt_timezone.utc
        )
        self.profile.save()
        result = self.client.get(path).json()["server_history"]
        self.assertEqual(result["first_joined_on"], "2026-02-01")
        self.profile.minecraft_visibility = "private"
        self.profile.save()
        self.assertNotIn("server_history", self.client.get(path).json())
        headers = self.auth_headers(
            self.session_token(self.login(username=self.user.username))
        )
        own = self.client.get(path, **headers).json()
        self.assertEqual(
            own["server_history"]["first_joined_on"], "2026-02-01"
        )
        self.assertNotIn("minecraft_first_joined_at", own)

    def test_self_cannot_claim_server_history_through_profile_update(self):
        headers = self.auth_headers(
            self.session_token(self.login(username=self.user.username))
        )
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
        )
        current = self.client.get("/api/profiles/me", **headers).json()
        payload = {key: current.get(key) or "" for key in fields}
        for field in ("minecraft_first_joined_at", "server_history"):
            result = self.patch_json(
                "/profiles/me", {**payload, field: "2026-01-01"}, **headers
            )
            self.assertEqual(result.status_code, 422, result.content)
        self.profile.refresh_from_db()
        self.assertEqual(
            self.profile.minecraft_first_joined_at.date(), date(2026, 1, 1)
        )
