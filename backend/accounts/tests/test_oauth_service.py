from __future__ import annotations

from unittest.mock import patch

from accounts.services.oauth import OAuthService
from django.test import TestCase
from ninja.errors import HttpError


class OAuthServiceTests(TestCase):
    @patch("accounts.services.oauth.registry.as_choices")
    @patch("accounts.services.oauth.SocialApp.objects.values_list")
    @patch("accounts.services.oauth.dj_settings")
    def test_configured_provider_ids_merge_db_and_settings(
        self,
        settings_mock,
        values_list_mock,
        as_choices_mock,
    ):
        values_list_mock.return_value = ["yandex"]
        settings_mock.SOCIALACCOUNT_PROVIDERS = {
            "github": {"APPS": [{"client_id": "id", "secret": "sec"}]},
            "unused": {},
        }
        as_choices_mock.return_value = [
            ("yandex", "Yandex"),
            ("github", "GitHub"),
        ]

        configured = OAuthService.configured_provider_ids()
        providers = OAuthService.list_providers()

        self.assertEqual(configured, {"yandex", "github"})
        self.assertEqual(
            providers,
            [
                {"id": "yandex", "name": "Yandex"},
                {"id": "github", "name": "GitHub"},
            ],
        )

    @patch("accounts.services.oauth.registry.as_choices")
    def test_link_provider_raises_404_for_unknown_provider(
        self, as_choices_mock
    ):
        as_choices_mock.return_value = [("yandex", "Yandex")]
        with self.assertRaises(HttpError) as ctx:
            OAuthService.link_provider("unknown")
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("accounts.services.oauth.registry.as_choices")
    @patch("accounts.services.oauth.reverse")
    @patch("accounts.services.oauth.dj_settings")
    def test_link_provider_returns_get_or_post_based_on_settings(
        self,
        settings_mock,
        reverse_mock,
        as_choices_mock,
    ):
        as_choices_mock.return_value = [("yandex", "Yandex")]
        reverse_mock.return_value = "/accounts/yandex/login/"

        settings_mock.SOCIALACCOUNT_LOGIN_ON_GET = True
        result_get = OAuthService.link_provider(
            "yandex", next_path="/account/security"
        )
        self.assertEqual(result_get["method"], "GET")
        self.assertIn("process=connect", result_get["authorize_url"])

        settings_mock.SOCIALACCOUNT_LOGIN_ON_GET = False
        result_post = OAuthService.link_provider(
            "yandex", next_path="/account/security"
        )
        self.assertEqual(result_post["method"], "POST")
