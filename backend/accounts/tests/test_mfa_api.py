from __future__ import annotations

from accounts.tests.base import APITestCase
from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from allauth.mfa.totp.internal.auth import (
    format_hotp_value,
    hotp_value,
    yield_hotp_counters_from_time,
)
from allauth.mfa.utils import decrypt
from django.contrib.auth import get_user_model
from django.test import override_settings


class HeadlessMfaApiTests(APITestCase):
    def _verify_primary_email(self, email: str) -> None:
        EmailAddress.objects.update_or_create(
            email=email.lower(),
            defaults={
                "user_id": self.user.pk,
                "primary": True,
                "verified": True,
            },
        )

    def _totp_code(self, secret: str) -> str:
        counter = next(yield_hotp_counters_from_time())
        return format_hotp_value(hotp_value(secret, counter))

    def _headless_get(self, path: str, **headers):
        return self.client.get(self.headless(path), **headers)

    def _setup_verified_user_with_session(self) -> tuple[str, str]:
        payload = self.signup_and_auth()
        self.user = self._user_from_email(payload["email"])
        self._verify_primary_email(payload["email"])
        return payload["email"], payload["session_token"]

    def _user_from_email(self, email: str):
        return get_user_model().objects.get(email=email.lower())

    def _activate_totp(self, session_token: str) -> str:
        self._reauthenticate(session_token)
        status = self._headless_get(
            "/account/authenticators/totp",
            **self.auth_headers(session_token),
        )
        self.assertEqual(status.status_code, 404, status.content)
        secret = status.json()["meta"]["secret"]
        response = self.headless_post_json(
            "/account/authenticators/totp",
            {"code": self._totp_code(secret)},
            **self.auth_headers(session_token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        return secret

    def _reauthenticate(self, session_token: str) -> None:
        response = self.headless_post_json(
            "/auth/reauthenticate",
            {"password": self.default_password},
            **self.auth_headers(session_token),
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_totp_activation_updates_authenticator_and_profile(self) -> None:
        email, session_token = self._setup_verified_user_with_session()

        status = self._headless_get(
            "/account/authenticators/totp",
            **self.auth_headers(session_token),
        )
        self.assertEqual(status.status_code, 404, status.content)
        self.assertTrue(status.json()["meta"]["secret"])
        self.assertIn("otpauth://totp/", status.json()["meta"]["totp_url"])

        self._reauthenticate(session_token)
        activate = self.headless_post_json(
            "/account/authenticators/totp",
            {"code": self._totp_code(status.json()["meta"]["secret"])},
            **self.auth_headers(session_token),
        )
        self.assertEqual(activate.status_code, 200, activate.content)

        me = self.client.get(
            self.api("/auth/me"),
            **self.auth_headers(session_token),
        )
        self.assertEqual(me.status_code, 200, me.content)
        self.assertTrue(me.json()["has_2fa"])

        authenticators = self._headless_get(
            "/account/authenticators",
            **self.auth_headers(session_token),
        )
        self.assertEqual(
            authenticators.status_code,
            200,
            authenticators.content,
        )
        data = authenticators.json()["data"]
        self.assertEqual(
            sorted(item["type"] for item in data),
            ["recovery_codes", "totp"],
        )

        totp_auth = Authenticator.objects.get(
            user=self._user_from_email(email),
            type=Authenticator.Type.TOTP,
        )
        self.assertTrue(decrypt(totp_auth.data["secret"]))

    def test_login_requires_mfa_then_accepts_totp_code(self) -> None:
        email, session_token = self._setup_verified_user_with_session()
        self._activate_totp(session_token)

        login = self.login(email=email, password=self.default_password)
        self.assertEqual(login.status_code, 401, login.content)
        payload = login.json()
        pending = next(
            flow
            for flow in payload["data"]["flows"]
            if flow["id"] == "mfa_authenticate"
        )
        self.assertIn("totp", pending["types"])
        login_session_token = self.session_token(login)
        self.assertTrue(login_session_token)

        auth = self.headless_post_json(
            "/auth/2fa/authenticate",
            {"code": self._totp_code(self._current_totp_secret(email))},
            **self.auth_headers(login_session_token),
        )
        self.assertEqual(auth.status_code, 200, auth.content)
        authenticated_session_token = (
            self.session_token(auth) or login_session_token
        )

        jwt = self.post_json(
            "/auth/jwt/from_session",
            {},
            **self.auth_headers(authenticated_session_token),
        )
        self.assertEqual(jwt.status_code, 200, jwt.content)
        self.assertTrue(jwt.json()["access"])

    def test_recovery_code_can_complete_mfa_and_decrements_unused_count(
        self,
    ) -> None:
        email, session_token = self._setup_verified_user_with_session()
        self._activate_totp(session_token)

        codes = self._headless_get(
            "/account/authenticators/recovery-codes",
            **self.auth_headers(session_token),
        )
        self.assertEqual(codes.status_code, 200, codes.content)
        recovery_code = codes.json()["data"]["unused_codes"][0]
        before_count = codes.json()["data"]["unused_code_count"]

        login = self.login(email=email, password=self.default_password)
        self.assertEqual(login.status_code, 401, login.content)
        login_session_token = self.session_token(login)
        self.assertTrue(login_session_token)

        auth = self.headless_post_json(
            "/auth/2fa/authenticate",
            {"code": recovery_code},
            **self.auth_headers(login_session_token),
        )
        self.assertEqual(auth.status_code, 200, auth.content)
        authenticated_session_token = (
            self.session_token(auth) or login_session_token
        )

        after = self._headless_get(
            "/account/authenticators/recovery-codes",
            **self.auth_headers(authenticated_session_token),
        )
        self.assertEqual(after.status_code, 200, after.content)
        self.assertEqual(
            after.json()["data"]["unused_code_count"],
            before_count - 1,
        )

    def test_sensitive_mfa_endpoints_require_recent_reauthentication(
        self,
    ) -> None:
        _email, session_token = self._setup_verified_user_with_session()
        self._activate_totp(session_token)

        with override_settings(ACCOUNT_REAUTHENTICATION_TIMEOUT=0):
            response = self._headless_get(
                "/account/authenticators/recovery-codes",
                **self.auth_headers(session_token),
            )
        self.assertEqual(response.status_code, 401, response.content)
        flow_ids = {flow["id"] for flow in response.json()["data"]["flows"]}
        self.assertIn("reauthenticate", flow_ids)
        self.assertIn("mfa_reauthenticate", flow_ids)

    def test_webauthn_endpoints_are_exposed_in_app_client(self) -> None:
        _email, session_token = self._setup_verified_user_with_session()

        config = self._headless_get("/config")
        self.assertEqual(config.status_code, 200, config.content)
        mfa = config.json()["data"]["mfa"]
        self.assertIn("webauthn", mfa["supported_types"])
        self.assertTrue(mfa["passkey_login_enabled"])

        self._reauthenticate(session_token)
        creation = self._headless_get(
            "/account/authenticators/webauthn",
            **self.auth_headers(session_token),
        )
        self.assertEqual(creation.status_code, 200, creation.content)
        self.assertIn("creation_options", creation.json()["data"])

        request_options = self._headless_get("/auth/webauthn/login")
        self.assertEqual(
            request_options.status_code,
            200,
            request_options.content,
        )
        self.assertIn("request_options", request_options.json()["data"])

    def _current_totp_secret(self, email: str) -> str:
        auth = Authenticator.objects.get(
            user=self._user_from_email(email),
            type=Authenticator.Type.TOTP,
        )
        return decrypt(auth.data["secret"])
