from __future__ import annotations

from unittest.mock import patch

from accounts.tests.base import APITestCase
from django.test import override_settings


class AccountStatusAndOAuthApiTests(APITestCase):
    def test_account_status_requires_auth(self):
        response = self.client.get(self.api("/account/status"))
        self.assertEqual(response.status_code, 401, response.content)

    def test_account_status_returns_missing_personalization_fields(self):
        payload = self.signup_and_auth()
        response = self.client.get(
            self.api("/account/status"),
            **self.auth_headers(payload["session_token"]),
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["profile_state"], "basic")
        self.assertEqual(data["profile_complete"], False)
        self.assertIn("vk_username", data["missing_fields"])
        self.assertIn("minecraft_nick", data["missing_fields"])
        self.assertIn("minecraft_has_license", data["missing_fields"])
        self.assertIn("is_itmo_student", data["missing_fields"])

    def test_oauth_providers_requires_auth(self):
        response = self.client.get(self.api("/oauth/providers"))
        self.assertEqual(response.status_code, 401, response.content)

    def test_oauth_link_requires_auth(self):
        response = self.client.get(self.api("/oauth/link/yandex"))
        self.assertEqual(response.status_code, 401, response.content)

    @patch("accounts.services.oauth.OAuthService.list_providers")
    def test_oauth_providers_returns_configured_list(
        self, list_providers_mock
    ):
        list_providers_mock.return_value = [{"id": "yandex", "name": "Yandex"}]
        payload = self.signup_and_auth()

        response = self.client.get(
            self.api("/oauth/providers"),
            **self.auth_headers(payload["session_token"]),
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            response.json()["providers"],
            list_providers_mock.return_value,
        )

    @override_settings(FF_PROFILE_PERSONALIZATION_ENFORCE=True)
    def test_oauth_link_blocks_incomplete_profile_when_enforced(self):
        payload = self.signup_and_auth()
        response = self.client.get(
            self.api("/oauth/link/yandex"),
            **self.auth_headers(payload["session_token"]),
        )
        self.assertEqual(response.status_code, 403, response.content)
        data = response.json()
        self.assertEqual(
            data["error_code"], "PROFILE_PERSONALIZATION_REQUIRED"
        )
        self.assertIn("PROFILE_FIELDS_INCOMPLETE", data["blocking_reasons"])

    @override_settings(FF_PROFILE_PERSONALIZATION_ENFORCE=False)
    @patch("accounts.services.oauth.OAuthService.link_provider")
    def test_oauth_link_returns_authorize_url_when_allowed(
        self, link_provider_mock
    ):
        payload = self.signup_and_auth()
        link_provider_mock.return_value = {
            "authorize_url": "/accounts/yandex/login/?process=connect",
            "method": "POST",
        }

        response = self.client.get(
            self.api("/oauth/link/yandex"),
            {"next": "/account/security"},
            **self.auth_headers(payload["session_token"]),
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            response.json()["authorize_url"],
            "/accounts/yandex/login/?process=connect",
        )
        self.assertEqual(response.json()["method"], "POST")
        link_provider_mock.assert_called_once_with(
            "yandex", next_path="/account/security"
        )

    @override_settings(FF_PROFILE_PERSONALIZATION_ENFORCE=False)
    def test_oauth_link_returns_404_for_unknown_provider(self):
        payload = self.signup_and_auth()
        response = self.client.get(
            self.api("/oauth/link/not_exists"),
            **self.auth_headers(payload["session_token"]),
        )
        self.assertEqual(response.status_code, 404, response.content)
