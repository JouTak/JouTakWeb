from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

from accounts.services.oauth import OAuthService
from django.test import RequestFactory, TestCase
from ninja.errors import HttpError


class OAuthServiceTests(TestCase):
    def setUp(self) -> None:
        self.request = RequestFactory().get("/oauth/providers")

    def test_sanitize_next_path_keeps_safe_relative_path(self) -> None:
        self.assertEqual(
            OAuthService.sanitize_next_path("/account/security"),
            "/account/security",
        )

    def test_sanitize_next_path_rejects_external_url(self) -> None:
        self.assertEqual(
            OAuthService.sanitize_next_path("https://evil.example/steal"),
            "/account/security",
        )

    def test_sanitize_next_path_rejects_protocol_relative_url(self) -> None:
        self.assertEqual(
            OAuthService.sanitize_next_path("//evil.example/steal"),
            "/account/security",
        )

    @patch("accounts.services.oauth.get_socialaccount_adapter")
    @patch("accounts.services.oauth.registry.get_class_list")
    def test_list_providers_uses_allauth_adapter_list_apps(
        self,
        get_class_list_mock: Mock,
        get_adapter_mock: Mock,
    ) -> None:
        app_yandex = Mock(provider="yandex")
        app_github = Mock(provider="github")
        adapter = get_adapter_mock.return_value
        adapter.list_apps.return_value = [app_yandex, app_github]
        provider_yandex = SimpleNamespace(id="yandex", name="Yandex")
        provider_github = SimpleNamespace(id="github", name="GitHub")
        provider_unused = SimpleNamespace(id="vk", name="VK")
        get_class_list_mock.return_value = [
            provider_yandex,
            provider_github,
            provider_unused,
        ]

        configured = OAuthService.configured_provider_ids(self.request)
        providers = OAuthService.list_providers(self.request)

        self.assertEqual(configured, {"yandex", "github"})
        self.assertEqual(
            providers,
            [
                {"id": "yandex", "name": "Yandex"},
                {"id": "github", "name": "GitHub"},
            ],
        )

    @patch("accounts.services.oauth.registry.get_class")
    def test_link_provider_raises_404_for_unknown_provider(
        self,
        get_class_mock: Mock,
    ) -> None:
        get_class_mock.return_value = None
        with self.assertRaises(HttpError) as ctx:
            OAuthService.link_provider(self.request, "unknown")
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("accounts.services.oauth.get_socialaccount_adapter")
    @patch("accounts.services.oauth.registry.get_class")
    @patch("accounts.services.oauth.reverse")
    @patch("accounts.services.oauth.dj_settings")
    def test_link_provider_returns_get_or_post_based_on_settings(
        self,
        settings_mock: Mock,
        reverse_mock: Mock,
        get_class_mock: Mock,
        get_adapter_mock: Mock,
    ) -> None:
        get_class_mock.return_value = Mock(uses_apps=True)
        get_adapter_mock.return_value.get_app.return_value = Mock()
        reverse_mock.return_value = "/accounts/yandex/login/"

        settings_mock.SOCIALACCOUNT_LOGIN_ON_GET = True
        result_get = OAuthService.link_provider(
            self.request,
            "yandex",
            next_path="/account/security",
        )
        self.assertEqual(result_get["method"], "GET")
        self.assertIn("process=connect", result_get["authorize_url"])

        settings_mock.SOCIALACCOUNT_LOGIN_ON_GET = False
        result_post = OAuthService.link_provider(
            self.request,
            "yandex",
            next_path="/account/security",
        )
        self.assertEqual(result_post["method"], "POST")
