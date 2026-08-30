from __future__ import annotations

import time
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from allauth.account.internal.flows.login import (
    AUTHENTICATION_METHODS_SESSION_KEY,
)
from allauth.core import context as allauth_context
from allauth.mfa.models import Authenticator
from allauth.mfa.recovery_codes.internal.auth import RecoveryCodes
from allauth.mfa.totp.internal.auth import (
    TOTP,
    format_hotp_value,
    generate_totp_secret,
    hotp_value,
    yield_hotp_counters_from_time,
)
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.test import Client, RequestFactory, TestCase, override_settings
from django.views.debug import SafeExceptionReporterFilter

from backend.admin_site import (
    ADMIN_MFA_PENDING_TTL_SECONDS,
    ADMIN_PASSKEY_UNAVAILABLE_ERROR,
    SESSION_KEY_ADMIN_MFA_PENDING_AUTH_HASH,
    SESSION_KEY_ADMIN_MFA_PENDING_ISSUED_AT,
    SESSION_KEY_ADMIN_MFA_PENDING_USER,
    SESSION_KEY_ADMIN_MFA_VERIFIED,
)
from backend.middleware import is_admin_mfa_path

User = get_user_model()


def _activate_totp(user) -> tuple[Authenticator, str]:
    secret = generate_totp_secret()
    authenticator = TOTP.activate(user, secret).instance
    counter = next(yield_hotp_counters_from_time())
    code = format_hotp_value(hotp_value(secret, counter))
    return authenticator, code


def _install_pending_mfa_session(
    client,
    user,
    *,
    issued_at: float | None = None,
    auth_hash: str | None = None,
) -> None:
    session = SessionStore()
    session[SESSION_KEY_ADMIN_MFA_PENDING_USER] = user.pk
    session[SESSION_KEY_ADMIN_MFA_PENDING_ISSUED_AT] = (
        time.time() if issued_at is None else issued_at
    )
    session[SESSION_KEY_ADMIN_MFA_PENDING_AUTH_HASH] = (
        user.get_session_auth_hash() if auth_hash is None else auth_hash
    )
    session.save()
    client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key


@override_settings(
    DJANGO_ALLOWED_HOSTS=(
        "localhost",
        "127.0.0.1",
        "admin.localhost",
        "api.localhost",
    ),
    DJANGO_ADMIN_HOSTS=("admin.localhost",),
    DJANGO_API_HOSTS=("api.localhost",),
    FRONTEND_BASE_URL="http://localhost:8080",
)
class AdminHostPolicyTests(TestCase):
    def assert_admin_login_redirect(self, response, expected_next: str):
        self.assertEqual(response.status_code, 302)
        location = urlsplit(response["Location"])
        self.assertEqual(location.path, "/admin/login/")
        self.assertEqual(parse_qs(location.query).get("next"), [expected_next])

    def test_mfa_template_renders_totp_autofocus_without_passkeys(self):
        html = render_to_string(
            "admin/mfa_verify.html",
            {
                "title": "Подтверждение входа",
                "site_title": "JouTak Staff Admin",
                "site_header": "JouTak Staff Admin",
                "username": "staff",
                "has_passkeys": False,
                "has_code_factors": True,
                "passkey_cross_host_blocked": False,
            },
        )

        self.assertIn('id="id_mfa_code"', html)
        self.assertIn("autofocus", html)
        self.assertIn('formaction="/admin/mfa-verify/cancel/"', html)
        self.assertNotIn("{%", html)

    def test_mfa_template_renders_passkey_flow_without_totp_autofocus(self):
        html = render_to_string(
            "admin/mfa_verify.html",
            {
                "title": "Подтверждение входа",
                "site_title": "JouTak Staff Admin",
                "site_header": "JouTak Staff Admin",
                "username": "staff",
                "has_passkeys": True,
                "has_code_factors": True,
                "passkey_cross_host_blocked": False,
            },
        )

        self.assertIn('id="passkey-section"', html)
        code_input = html.split('id="id_mfa_code"', maxsplit=1)[1].split(
            "/>", maxsplit=1
        )[0]
        self.assertNotIn("autofocus", code_input)
        self.assertIn('method: "POST"', html)
        self.assertNotIn("{%", html)

    def test_mfa_middleware_exempts_only_exact_authentication_routes(self):
        for path in (
            "/admin/login/",
            "/admin/mfa-verify/",
            "/admin/mfa-verify/cancel/",
            "/admin/mfa-verify/webauthn-options/",
            "/admin/mfa-verify/webauthn-complete/",
        ):
            self.assertFalse(is_admin_mfa_path(path), path)

        for path in (
            "/admin/",
            "/admin/login/unwrapped-view/",
            "/admin/mfa-verify/unwrapped-view/",
        ):
            self.assertTrue(is_admin_mfa_path(path), path)

    def test_admin_host_redirects_root_to_admin(self):
        response = self.client.get("/", HTTP_HOST="admin.localhost")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/")

    def test_admin_host_allows_admin_login(self):
        response = self.client.get(
            "/admin/login/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_admin_login_post_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)

        response = csrf_client.post(
            "/admin/login/",
            {"username": "staff", "password": "password-secret"},
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 403)

    @override_settings(DEBUG=False)
    def test_admin_login_marks_password_sensitive_before_errors(self):
        password = "password-visible-only-to-the-login-form"
        request = RequestFactory().post(
            "/admin/login/",
            {"username": "staff", "password": password},
            HTTP_HOST="admin.localhost",
        )
        request._dont_enforce_csrf_checks = True

        with (
            patch.object(
                admin.site,
                "login_form",
                side_effect=RuntimeError("synthetic login failure"),
            ),
            self.assertRaisesRegex(RuntimeError, "synthetic login failure"),
        ):
            admin.site.login(request)

        self.assertEqual(request.sensitive_post_parameters, ("password",))
        cleansed = SafeExceptionReporterFilter().get_post_parameters(request)
        self.assertNotEqual(cleansed["password"], password)
        self.assertEqual(
            cleansed["password"],
            SafeExceptionReporterFilter.cleansed_substitute,
        )

    @override_settings(DEBUG=False)
    def test_admin_mfa_marks_code_sensitive_before_errors(self):
        mfa_code = "recovery-code-visible-only-to-the-mfa-form"
        request = RequestFactory().post(
            "/admin/mfa-verify/",
            {"mfa_code": mfa_code},
            HTTP_HOST="admin.localhost",
        )

        with (
            patch.object(
                admin.site,
                "_get_pending_user",
                side_effect=RuntimeError("synthetic MFA failure"),
            ),
            self.assertRaisesRegex(RuntimeError, "synthetic MFA failure"),
        ):
            admin.site.mfa_verify_view(request)

        self.assertEqual(request.sensitive_post_parameters, ("mfa_code",))
        cleansed = SafeExceptionReporterFilter().get_post_parameters(request)
        self.assertNotEqual(cleansed["mfa_code"], mfa_code)
        self.assertEqual(
            cleansed["mfa_code"],
            SafeExceptionReporterFilter.cleansed_substitute,
        )

    @patch("backend.admin_site.admin_mfa_is_enabled", return_value=False)
    def test_admin_login_rejects_staff_without_mfa(self, _mocked):
        user = User.objects.create_user(
            username="staff_login_no_mfa",
            email="staff-login-no-mfa@example.com",
            password="StrongPass123!",
            is_staff=True,
        )

        response = self.client.post(
            "/admin/login/",
            {
                "username": user.username,
                "password": "StrongPass123!",
                "next": "/admin/",
            },
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Для доступа в админку необходим настроенный 2FA.",
        )
        self.assertContains(
            response,
            'href="http://localhost:8080/account/security#mfa"',
        )

    def test_admin_host_blocks_bff_surface(self):
        response = self.client.get(
            "/bff/bootstrap",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 403)

    def test_api_host_blocks_admin_surface(self):
        response = self.client.get("/admin/login/", HTTP_HOST="api.localhost")

        self.assertEqual(response.status_code, 403)

    def test_unknown_host_blocks_admin_surface(self):
        """Hosts not in ADMIN/API lists cannot access /admin/."""
        response = self.client.get("/admin/login/", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 403)

    def test_non_staff_user_cannot_access_admin(self):
        user = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(user)

        response = self.client.get("/admin/", HTTP_HOST="admin.localhost")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    @patch("backend.middleware.admin_mfa_is_enabled", return_value=False)
    def test_staff_without_mfa_enrolled_is_denied_by_middleware(self, _mocked):
        user = User.objects.create_user(
            username="staff_no_mfa",
            email="staff-no-mfa@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get("/admin/", HTTP_HOST="admin.localhost")

        self.assert_admin_login_redirect(response, "/admin/")

    @patch("backend.admin_site.admin_mfa_is_enabled", return_value=False)
    def test_staff_without_mfa_can_open_login_without_redirect_loop(
        self, _mocked
    ):
        user = User.objects.create_user(
            username="staff_no_mfa_login",
            email="staff-no-mfa-login@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(
            "/admin/login/?next=%2Fadmin%2F",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 200)

    @patch("backend.admin_site.admin_mfa_is_enabled", return_value=False)
    @patch("backend.middleware.admin_mfa_is_enabled", return_value=True)
    @patch("backend.middleware.is_admin_mfa_verified", return_value=True)
    def test_admin_site_also_denies_staff_without_mfa(
        self, _mock_verified, _mock_middleware_enabled, _mock_admin_enabled
    ):
        user = User.objects.create_user(
            username="staff_no_mfa_admin_site",
            email="staff-no-mfa-admin-site@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.client.force_login(user)
        session = self.client.session
        session[SESSION_KEY_ADMIN_MFA_VERIFIED] = True
        session.save()

        response = self.client.get("/admin/", HTTP_HOST="admin.localhost")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    @patch("backend.middleware.admin_mfa_is_enabled", return_value=True)
    def test_staff_with_mfa_enrolled_but_unverified_is_redirected(
        self, _mocked
    ):
        user = User.objects.create_user(
            username="staff_mfa_unverified",
            email="staff-mfa-unverified@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(
            "/admin/?section=accounts",
            HTTP_HOST="admin.localhost",
        )

        self.assert_admin_login_redirect(
            response,
            "/admin/?section=accounts",
        )

    @patch("backend.admin_site.admin_mfa_is_enabled", return_value=True)
    @patch("backend.middleware.admin_mfa_is_enabled", return_value=True)
    @patch("backend.middleware.is_admin_mfa_verified", return_value=True)
    def test_staff_with_mfa_verified_can_access_admin(
        self, _mock_verified, _mock_middleware_enabled, _mock_admin_enabled
    ):
        user = User.objects.create_user(
            username="staff_yes_mfa",
            email="staff-yes-mfa@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.client.force_login(user)
        # Mark session as MFA-verified
        session = self.client.session
        session[SESSION_KEY_ADMIN_MFA_VERIFIED] = True
        session.save()

        response = self.client.get("/admin/", HTTP_HOST="admin.localhost")

        self.assertEqual(response.status_code, 200)

    @patch("backend.admin_site.admin_mfa_is_enabled", return_value=True)
    @patch("backend.middleware.admin_mfa_is_enabled", return_value=True)
    @patch("backend.middleware.is_admin_mfa_verified", return_value=True)
    def test_staff_can_open_registered_backoffice_models(
        self, _mock_verified, _mock_middleware_enabled, _mock_admin_enabled
    ):
        user = User.objects.create_user(
            username="staff_models",
            email="staff-models@example.com",
            password="StrongPass123!",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(user)
        session = self.client.session
        session[SESSION_KEY_ADMIN_MFA_VERIFIED] = True
        session.save()

        for path in (
            "/admin/auth/user/",
            "/admin/featureflags/featuredefinition/",
        ):
            response = self.client.get(path, HTTP_HOST="admin.localhost")
            self.assertEqual(response.status_code, 200, path)

    @patch("backend.admin_site.admin_mfa_is_enabled", return_value=True)
    def test_mfa_login_redirects_to_verify_page(self, _mocked):
        """Staff with MFA gets redirected to MFA verify after password."""
        user = User.objects.create_user(
            username="staff_mfa_login",
            email="staff-mfa-login@example.com",
            password="StrongPass123!",
            is_staff=True,
        )

        response = self.client.post(
            "/admin/login/",
            {
                "username": user.username,
                "password": "StrongPass123!",
                "next": "/admin/",
            },
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/mfa-verify/", response["Location"])
        session = self.client.session
        self.assertEqual(session[SESSION_KEY_ADMIN_MFA_PENDING_USER], user.pk)
        self.assertIn(SESSION_KEY_ADMIN_MFA_PENDING_ISSUED_AT, session)
        self.assertEqual(
            session[SESSION_KEY_ADMIN_MFA_PENDING_AUTH_HASH],
            user.get_session_auth_hash(),
        )

    @patch(
        "backend.admin_site.admin_mfa_is_enabled",
        side_effect=(True, False),
    )
    def test_admin_login_fails_closed_if_mfa_enrollment_disappears(
        self, _mocked
    ):
        user = User.objects.create_user(
            username="staff_mfa_race",
            email="staff-mfa-race@example.com",
            password="StrongPass123!",
            is_staff=True,
        )

        response = self.client.post(
            "/admin/login/",
            {
                "username": user.username,
                "password": "StrongPass123!",
                "next": "/admin/",
            },
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Для доступа в админку необходим настроенный 2FA.",
        )
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertNotIn(
            SESSION_KEY_ADMIN_MFA_PENDING_USER,
            self.client.session,
        )

    def test_mfa_verify_without_pending_session_redirects_to_login(
        self,
    ):
        """Accessing MFA verify without pending user redirects back."""
        response = self.client.get(
            "/admin/mfa-verify/", HTTP_HOST="admin.localhost"
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_pending_mfa_expires_after_short_ttl(self):
        user = User.objects.create_user(
            username="staff_mfa_expired",
            email="staff-mfa-expired@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        _activate_totp(user)

        with patch("backend.admin_site.time.time", return_value=1000.0):
            login_response = self.client.post(
                "/admin/login/",
                {
                    "username": user.username,
                    "password": "StrongPass123!",
                },
                HTTP_HOST="admin.localhost",
            )
        self.assertEqual(login_response.status_code, 302)

        with patch(
            "backend.admin_site.time.time",
            return_value=1001.0 + ADMIN_MFA_PENDING_TTL_SECONDS,
        ):
            response = self.client.get(
                "/admin/mfa-verify/",
                HTTP_HOST="admin.localhost",
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/login/")
        for key in (
            SESSION_KEY_ADMIN_MFA_PENDING_USER,
            SESSION_KEY_ADMIN_MFA_PENDING_ISSUED_AT,
            SESSION_KEY_ADMIN_MFA_PENDING_AUTH_HASH,
        ):
            self.assertNotIn(key, self.client.session)

    def test_pending_mfa_is_invalidated_when_password_hash_changes(self):
        user = User.objects.create_user(
            username="staff_mfa_password_changed",
            email="staff-mfa-password-changed@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        _activate_totp(user)
        login_response = self.client.post(
            "/admin/login/",
            {
                "username": user.username,
                "password": "StrongPass123!",
            },
            HTTP_HOST="admin.localhost",
        )
        self.assertEqual(login_response.status_code, 302)

        user.set_password("DifferentStrongPass123!")
        user.save(update_fields=("password",))
        response = self.client.get(
            "/admin/mfa-verify/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/login/")
        self.assertNotIn(
            SESSION_KEY_ADMIN_MFA_PENDING_USER,
            self.client.session,
        )

    def test_cancel_clears_pending_mfa_state(self):
        user = User.objects.create_user(
            username="staff_mfa_cancel",
            email="staff-mfa-cancel@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        _activate_totp(user)
        login_response = self.client.post(
            "/admin/login/",
            {
                "username": user.username,
                "password": "StrongPass123!",
            },
            HTTP_HOST="admin.localhost",
        )
        self.assertEqual(login_response.status_code, 302)

        response = self.client.post(
            "/admin/mfa-verify/cancel/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/login/")
        for key in (
            SESSION_KEY_ADMIN_MFA_PENDING_USER,
            SESSION_KEY_ADMIN_MFA_PENDING_ISSUED_AT,
            SESSION_KEY_ADMIN_MFA_PENDING_AUTH_HASH,
        ):
            self.assertNotIn(key, self.client.session)

    def test_totp_verification_records_usage_and_authentication_method(self):
        user = User.objects.create_user(
            username="staff_mfa_totp",
            email="staff-mfa-totp@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        authenticator, code = _activate_totp(user)
        login_response = self.client.post(
            "/admin/login/",
            {
                "username": user.username,
                "password": "StrongPass123!",
            },
            HTTP_HOST="admin.localhost",
        )
        self.assertEqual(login_response.status_code, 302)

        response = self.client.post(
            "/admin/mfa-verify/",
            {"mfa_code": code},
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/")
        authenticator.refresh_from_db()
        self.assertIsNotNone(authenticator.last_used_at)
        self.assertIs(
            self.client.session[SESSION_KEY_ADMIN_MFA_VERIFIED], True
        )
        methods = self.client.session[AUTHENTICATION_METHODS_SESSION_KEY]
        self.assertTrue(
            any(
                method.get("method") == "mfa"
                and method.get("type") == Authenticator.Type.TOTP
                for method in methods
            )
        )

    def test_recovery_code_verification_consumes_code_and_records_usage(self):
        user = User.objects.create_user(
            username="staff_mfa_recovery",
            email="staff-mfa-recovery@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        _activate_totp(user)
        recovery = RecoveryCodes.activate(user)
        code = recovery.get_unused_codes()[0]
        login_response = self.client.post(
            "/admin/login/",
            {
                "username": user.username,
                "password": "StrongPass123!",
            },
            HTTP_HOST="admin.localhost",
        )
        self.assertEqual(login_response.status_code, 302)

        response = self.client.post(
            "/admin/mfa-verify/",
            {"mfa_code": code},
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        recovery.instance.refresh_from_db()
        self.assertIsNotNone(recovery.instance.last_used_at)
        self.assertNotIn(code, recovery.get_unused_codes())

    @patch(
        "allauth.mfa.base.forms.check_rate_limit",
        side_effect=ValidationError(
            "Слишком много попыток.",
            code="too_many_login_attempts",
        ),
    )
    def test_totp_verification_uses_allauth_rate_limit(self, rate_limit_mock):
        user = User.objects.create_user(
            username="staff_mfa_limited",
            email="staff-mfa-limited@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        _activate_totp(user)
        _install_pending_mfa_session(self.client, user)

        response = self.client.post(
            "/admin/mfa-verify/",
            {"mfa_code": "000000"},
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Слишком много попыток.")
        rate_limit_mock.assert_called_once_with(user)
        self.assertNotIn(SESSION_KEY_ADMIN_MFA_VERIFIED, self.client.session)
        self.assertIn(SESSION_KEY_ADMIN_MFA_PENDING_USER, self.client.session)

    def test_cross_host_webauthn_only_shows_safe_setup_path(self):
        user = User.objects.create_user(
            username="staff_webauthn_cross_host",
            email="staff-webauthn-cross-host@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        Authenticator.objects.create(
            user=user,
            type=Authenticator.Type.WEBAUTHN,
            data={},
        )
        _install_pending_mfa_session(self.client, user)

        response = self.client.get(
            "/admin/mfa-verify/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="passkey-host-mismatch"')
        self.assertContains(
            response,
            'href="http://localhost:8080/account/security#mfa"',
        )
        self.assertNotContains(response, 'id="passkey-section"')
        self.assertNotContains(response, 'id="id_mfa_code"')
        self.assertNotContains(response, "startPasskeyAuth")
        self.assertNotIn(SESSION_KEY_ADMIN_MFA_VERIFIED, self.client.session)

    def test_cross_host_webauthn_endpoints_fail_closed(self):
        user = User.objects.create_user(
            username="staff_webauthn_cross_host_endpoints",
            email="staff-webauthn-cross-host-endpoints@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        Authenticator.objects.create(
            user=user,
            type=Authenticator.Type.WEBAUTHN,
            data={},
        )
        _install_pending_mfa_session(self.client, user)

        with patch(
            "allauth.mfa.webauthn.internal.auth.begin_authentication"
        ) as begin_mock:
            options_response = self.client.post(
                "/admin/mfa-verify/webauthn-options/",
                HTTP_HOST="admin.localhost",
            )
        with patch(
            "allauth.mfa.webauthn.internal.auth.complete_authentication"
        ) as complete_mock:
            complete_response = self.client.post(
                "/admin/mfa-verify/webauthn-complete/",
                data='{"id":"credential","response":{}}',
                content_type="application/json",
                HTTP_HOST="admin.localhost",
            )

        for response in (options_response, complete_response):
            self.assertEqual(response.status_code, 409)
            self.assertJSONEqual(
                response.content,
                {"error": ADMIN_PASSKEY_UNAVAILABLE_ERROR},
            )
        begin_mock.assert_not_called()
        complete_mock.assert_not_called()
        self.assertNotIn(SESSION_KEY_ADMIN_MFA_VERIFIED, self.client.session)

    def test_cross_host_totp_remains_available_with_enrolled_passkey(self):
        user = User.objects.create_user(
            username="staff_totp_cross_host",
            email="staff-totp-cross-host@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        _, code = _activate_totp(user)
        Authenticator.objects.create(
            user=user,
            type=Authenticator.Type.WEBAUTHN,
            data={},
        )
        _install_pending_mfa_session(self.client, user)

        page_response = self.client.get(
            "/admin/mfa-verify/",
            HTTP_HOST="admin.localhost",
        )
        verify_response = self.client.post(
            "/admin/mfa-verify/",
            {"mfa_code": code},
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, 'id="id_mfa_code"')
        self.assertNotContains(page_response, 'id="passkey-section"')
        self.assertNotContains(page_response, 'id="passkey-host-mismatch"')
        self.assertEqual(verify_response.status_code, 302)
        self.assertIs(
            self.client.session[SESSION_KEY_ADMIN_MFA_VERIFIED], True
        )

    @override_settings(DJANGO_API_HOSTS=("ADMIN.LOCALHOST:443",))
    @patch(
        "allauth.mfa.webauthn.internal.auth.begin_authentication",
        return_value={"challenge": "same-host-challenge"},
    )
    def test_same_host_with_different_ports_preserves_passkey(
        self, begin_mock
    ):
        user = User.objects.create_user(
            username="staff_webauthn_same_host",
            email="staff-webauthn-same-host@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        Authenticator.objects.create(
            user=user,
            type=Authenticator.Type.WEBAUTHN,
            data={},
        )
        _install_pending_mfa_session(self.client, user)

        page_response = self.client.get(
            "/admin/mfa-verify/",
            HTTP_HOST="admin.localhost:8443",
        )
        options_response = self.client.post(
            "/admin/mfa-verify/webauthn-options/",
            HTTP_HOST="admin.localhost:8443",
        )

        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, 'id="passkey-section"')
        self.assertNotContains(page_response, 'id="passkey-host-mismatch"')
        self.assertNotContains(page_response, 'id="id_mfa_code"')
        self.assertEqual(options_response.status_code, 200)
        begin_mock.assert_called_once_with(user=user)

    def test_webauthn_options_requires_csrf_protected_post(self):
        user = User.objects.create_user(
            username="staff_webauthn_csrf",
            email="staff-webauthn-csrf@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        Authenticator.objects.create(
            user=user,
            type=Authenticator.Type.WEBAUTHN,
            data={},
        )
        csrf_client = Client(enforce_csrf_checks=True)
        _install_pending_mfa_session(csrf_client, user)

        response = csrf_client.post(
            "/admin/mfa-verify/webauthn-options/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 403)

    @override_settings(DJANGO_API_HOSTS=("admin.localhost",))
    @patch(
        "allauth.mfa.webauthn.internal.auth.begin_authentication",
        return_value={"challenge": "test-challenge"},
    )
    def test_webauthn_options_restores_allauth_request_context(
        self, begin_mock
    ):
        user = User.objects.create_user(
            username="staff_webauthn_options",
            email="staff-webauthn-options@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        Authenticator.objects.create(
            user=user,
            type=Authenticator.Type.WEBAUTHN,
            data={},
        )
        _install_pending_mfa_session(self.client, user)
        outer_request = object()

        get_response = self.client.get(
            "/admin/mfa-verify/webauthn-options/",
            HTTP_HOST="admin.localhost",
        )
        self.assertEqual(get_response.status_code, 405)

        with allauth_context.request_context(outer_request):
            response = self.client.post(
                "/admin/mfa-verify/webauthn-options/",
                HTTP_HOST="admin.localhost",
            )
            self.assertIs(allauth_context.request, outer_request)

        self.assertEqual(response.status_code, 200)
        begin_mock.assert_called_once_with(user=user)
        self.assertIsNone(allauth_context.request)
        self.assertNotIn("request", vars(allauth_context))

    @override_settings(DJANGO_API_HOSTS=("admin.localhost",))
    @patch(
        "allauth.mfa.webauthn.internal.auth.parse_authentication_response",
        return_value=None,
    )
    def test_webauthn_verification_records_usage_and_authentication_method(
        self, _mock_parse
    ):
        user = User.objects.create_user(
            username="staff_webauthn_success",
            email="staff-webauthn-success@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        authenticator = Authenticator.objects.create(
            user=user,
            type=Authenticator.Type.WEBAUTHN,
            data={},
        )
        _install_pending_mfa_session(self.client, user)
        credential = {"id": "credential", "response": {}}

        with patch(
            "allauth.mfa.webauthn.internal.auth.complete_authentication",
            return_value=authenticator,
        ) as complete_mock:
            response = self.client.post(
                "/admin/mfa-verify/webauthn-complete/",
                data='{"id":"credential","response":{}}',
                content_type="application/json",
                HTTP_HOST="admin.localhost",
            )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {"ok": True, "redirect": "/admin/"},
        )
        complete_mock.assert_called_once_with(user, credential)
        authenticator.refresh_from_db()
        self.assertIsNotNone(authenticator.last_used_at)
        methods = self.client.session[AUTHENTICATION_METHODS_SESSION_KEY]
        self.assertTrue(
            any(
                method.get("method") == "mfa"
                and method.get("type") == Authenticator.Type.WEBAUTHN
                for method in methods
            )
        )
        self.assertIs(
            self.client.session[SESSION_KEY_ADMIN_MFA_VERIFIED], True
        )

    @override_settings(DJANGO_API_HOSTS=("admin.localhost",))
    @patch(
        "allauth.mfa.webauthn.internal.auth.parse_authentication_response",
        return_value=None,
    )
    @patch(
        "allauth.mfa.webauthn.forms.check_rate_limit",
        side_effect=ValidationError(
            "Слишком много попыток.",
            code="too_many_login_attempts",
        ),
    )
    def test_webauthn_verification_uses_allauth_rate_limit(
        self, rate_limit_mock, _mock_parse
    ):
        user = User.objects.create_user(
            username="staff_webauthn_limited",
            email="staff-webauthn-limited@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        Authenticator.objects.create(
            user=user,
            type=Authenticator.Type.WEBAUTHN,
            data={},
        )
        _install_pending_mfa_session(self.client, user)

        response = self.client.post(
            "/admin/mfa-verify/webauthn-complete/",
            data='{"id":"credential","response":{}}',
            content_type="application/json",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 429)
        self.assertJSONEqual(
            response.content,
            {"error": "Слишком много попыток."},
        )
        rate_limit_mock.assert_called_once_with(user)
        self.assertNotIn(SESSION_KEY_ADMIN_MFA_VERIFIED, self.client.session)
        self.assertIn(SESSION_KEY_ADMIN_MFA_PENDING_USER, self.client.session)

    @override_settings(DJANGO_API_HOSTS=("admin.localhost",))
    @patch(
        "allauth.mfa.webauthn.internal.auth.complete_authentication",
        side_effect=ValueError("boom"),
    )
    @patch(
        "allauth.mfa.webauthn.internal.auth.parse_authentication_response",
        return_value=None,
    )
    def test_webauthn_complete_logs_failure_and_returns_400(
        self, _mock_parse, _mock_complete
    ):
        user = User.objects.create_user(
            username="staff_webauthn",
            email="staff-webauthn@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        Authenticator.objects.create(
            user=user,
            type=Authenticator.Type.WEBAUTHN,
            data={},
        )
        _install_pending_mfa_session(self.client, user)
        outer_request = object()

        with allauth_context.request_context(outer_request):
            with patch("backend.admin_site.logger.warning") as warning_mock:
                response = self.client.post(
                    "/admin/mfa-verify/webauthn-complete/",
                    data='{"id":"credential","response":{}}',
                    content_type="application/json",
                    HTTP_HOST="admin.localhost",
                )
            self.assertIs(allauth_context.request, outer_request)

        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            response.content,
            {"error": "Verification failed"},
        )
        warning_mock.assert_called_once()
        self.assertTrue(warning_mock.call_args.kwargs.get("exc_info"))
        self.assertIsNone(allauth_context.request)
        self.assertNotIn("request", vars(allauth_context))
