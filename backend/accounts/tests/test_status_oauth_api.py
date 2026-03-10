from __future__ import annotations

from unittest.mock import Mock, patch

from accounts.tests.base import APITestCase
from core.models import UserSessionMeta
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone

User = get_user_model()


class AccountStatusAndOAuthApiTests(APITestCase):
    def _revoke_token(self, user: User, token: str) -> None:
        session = self.client.session
        if not session.session_key:
            session["test"] = "1"
            session.save()
        session_key = session.session_key or token
        UserSessionMeta.objects.update_or_create(
            user=user,
            session_key=session_key,
            defaults={
                "session_token": token,
                "revoked_reason": "manual",
                "revoked_at": timezone.now(),
            },
        )

    def test_account_status_requires_auth(self) -> None:
        response = self.client.get(self.api("/account/status"))
        self.assertEqual(response.status_code, 401, response.content)

    def test_account_status_returns_missing_personalization_fields(
        self,
    ) -> None:
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

    def test_oauth_providers_requires_auth(self) -> None:
        response = self.client.get(self.api("/oauth/providers"))
        self.assertEqual(response.status_code, 401, response.content)

    def test_oauth_providers_rejects_revoked_session(self) -> None:
        payload = self.signup_and_auth()
        token = payload["session_token"]
        user = User.objects.get(email=payload["email"].lower())
        self._revoke_token(user, token)
        response = self.client.get(
            self.api("/oauth/providers"),
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 401, response.content)
        self.assertEqual(response.json()["detail"], "session revoked")

    def test_oauth_link_requires_auth(self) -> None:
        response = self.client.get(self.api("/oauth/link/yandex"))
        self.assertEqual(response.status_code, 401, response.content)

    @patch("accounts.services.oauth.OAuthService.list_providers")
    def test_oauth_providers_returns_configured_list(
        self,
        list_providers_mock: Mock,
    ) -> None:
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
    def test_oauth_link_blocks_incomplete_profile_when_enforced(self) -> None:
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
        self,
        link_provider_mock: Mock,
    ) -> None:
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
            response.wsgi_request,
            "yandex",
            next_path="/account/security",
        )

    @override_settings(FF_PROFILE_PERSONALIZATION_ENFORCE=False)
    @patch("accounts.services.oauth.OAuthService.link_provider")
    def test_oauth_link_sanitizes_unsafe_next_path(
        self,
        link_provider_mock: Mock,
    ) -> None:
        payload = self.signup_and_auth()
        link_provider_mock.return_value = {
            "authorize_url": "/accounts/yandex/login/?process=connect",
            "method": "POST",
        }

        response = self.client.get(
            self.api("/oauth/link/yandex"),
            {"next": "https://evil.example/steal"},
            **self.auth_headers(payload["session_token"]),
        )
        self.assertEqual(response.status_code, 200, response.content)
        link_provider_mock.assert_called_once_with(
            response.wsgi_request,
            "yandex",
            next_path="/account/security",
        )

    @override_settings(FF_PROFILE_PERSONALIZATION_ENFORCE=False)
    def test_oauth_link_returns_404_for_unknown_provider(self) -> None:
        payload = self.signup_and_auth()
        response = self.client.get(
            self.api("/oauth/link/not_exists"),
            **self.auth_headers(payload["session_token"]),
        )
        self.assertEqual(response.status_code, 404, response.content)
