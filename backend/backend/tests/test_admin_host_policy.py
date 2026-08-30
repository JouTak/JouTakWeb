from __future__ import annotations

import base64
import json
import time
from unittest.mock import patch

from accounts.services.admin_mfa import AdminMFAVerificationError
from allauth.core import context as allauth_context
from allauth.mfa.models import Authenticator
from allauth.mfa.totp.internal.auth import TOTP
from allauth.mfa.webauthn.internal import auth as allauth_webauthn
from django.conf import settings
from django.contrib.auth import (
    BACKEND_SESSION_KEY,
    HASH_SESSION_KEY,
    SESSION_KEY,
    get_user_model,
)
from django.contrib.sessions.backends.db import SessionStore
from django.template.loader import render_to_string
from django.test import TestCase, override_settings

from backend.admin_site import (
    SESSION_KEY_ADMIN_MFA_PENDING_USER,
    SESSION_KEY_ADMIN_MFA_VERIFIED,
)

User = get_user_model()


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
    WEBAUTHN_ADMIN_ORIGINS=("http://admin.localhost",),
)
class AdminHostPolicyTests(TestCase):
    def _activate_totp(self, user) -> Authenticator:
        return TOTP.activate(
            user,
            "JBSWY3DPEHPK3PXP",
        ).instance

    def _mark_admin_assured(self, user, method="totp") -> None:
        session = self.client.session
        session[SESSION_KEY_ADMIN_MFA_VERIFIED] = {
            "version": 1,
            "user_pk": str(user.pk),
            "verified_at": time.time(),
            "method": method,
        }
        session.save()

    def test_mfa_template_renders_totp_autofocus_without_passkeys(self):
        html = render_to_string(
            "admin/mfa_verify.html",
            {
                "title": "Подтверждение входа",
                "site_title": "JouTak Staff Admin",
                "site_header": "JouTak Staff Admin",
                "username": "staff",
                "has_passkeys": False,
            },
        )

        self.assertIn('id="id_mfa_code"', html)
        self.assertIn("autofocus", html)
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
            },
        )

        self.assertIn('id="passkey-section"', html)
        code_input = html.split('id="id_mfa_code"', maxsplit=1)[1].split(
            "/>", maxsplit=1
        )[0]
        self.assertNotIn("autofocus", code_input)
        self.assertNotIn("{%", html)

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

    def test_anonymous_cannot_access_protected_admin_page(self):
        response = self.client.get(
            "/admin/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_inactive_staff_cannot_access_protected_admin_page(self):
        user = User.objects.create_user(
            username="inactive_staff",
            email="inactive-staff@example.com",
            password="StrongPass123!",
            is_staff=True,
            is_active=False,
        )
        self._activate_totp(user)
        self.client.force_login(user)
        self._mark_admin_assured(user)

        response = self.client.get(
            "/admin/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
        self.assertNotIn(
            SESSION_KEY_ADMIN_MFA_VERIFIED,
            self.client.session,
        )

    def test_admin_login_rejects_staff_without_mfa(self):
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
            HTTP_ORIGIN="http://admin.localhost",
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

    def test_staff_without_mfa_enrolled_is_denied_by_middleware(self):
        user = User.objects.create_user(
            username="staff_no_mfa",
            email="staff-no-mfa@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get("/admin/", HTTP_HOST="admin.localhost")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_staff_with_mfa_verified_can_access_admin(self):
        user = User.objects.create_user(
            username="staff_yes_mfa",
            email="staff-yes-mfa@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self._activate_totp(user)
        self.client.force_login(user)
        self._mark_admin_assured(user)

        response = self.client.get("/admin/", HTTP_HOST="admin.localhost")

        self.assertEqual(response.status_code, 200)

    def test_enrolled_force_login_without_assurance_is_denied(self):
        user = User.objects.create_user(
            username="staff_stale_session",
            email="staff-stale-session@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self._activate_totp(user)
        self.client.force_login(user)

        response = self.client.get(
            "/admin/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_frontend_app_session_token_does_not_authorize_admin(self):
        user = User.objects.create_user(
            username="frontend_token_staff",
            email="frontend-token-staff@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self._activate_totp(user)
        frontend_session = SessionStore()
        frontend_session[SESSION_KEY] = str(user.pk)
        frontend_session[BACKEND_SESSION_KEY] = (
            "django.contrib.auth.backends.ModelBackend"
        )
        frontend_session[HASH_SESSION_KEY] = user.get_session_auth_hash()
        frontend_session.save()

        response = self.client.get(
            "/admin/",
            HTTP_HOST="admin.localhost",
            HTTP_X_SESSION_TOKEN=frontend_session.session_key,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_staff_can_open_registered_backoffice_models(self):
        user = User.objects.create_user(
            username="staff_models",
            email="staff-models@example.com",
            password="StrongPass123!",
            is_staff=True,
            is_superuser=True,
        )
        self._activate_totp(user)
        self.client.force_login(user)
        self._mark_admin_assured(user)

        for path in (
            "/admin/auth/user/",
            "/admin/featureflags/featuredefinition/",
        ):
            response = self.client.get(path, HTTP_HOST="admin.localhost")
            self.assertEqual(response.status_code, 200, path)

    def test_mfa_login_redirects_to_verify_page(self):
        """Staff with MFA gets redirected to MFA verify after password."""
        user = User.objects.create_user(
            username="staff_mfa_login",
            email="staff-mfa-login@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self._activate_totp(user)

        response = self.client.post(
            "/admin/login/",
            {
                "username": user.username,
                "password": "StrongPass123!",
                "next": "/admin/",
            },
            HTTP_HOST="admin.localhost",
            HTTP_ORIGIN="http://admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/mfa-verify/", response["Location"])

    def test_mfa_verify_without_pending_session_redirects_to_login(
        self,
    ):
        """Accessing MFA verify without pending user redirects back."""
        response = self.client.get(
            "/admin/mfa-verify/", HTTP_HOST="admin.localhost"
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    @patch(
        "backend.admin_site.verify_admin_webauthn",
        side_effect=AdminMFAVerificationError("incorrect_webauthn"),
    )
    def test_webauthn_complete_logs_failure_and_returns_400(
        self, _mock_complete
    ):
        user = User.objects.create_user(
            username="staff_webauthn",
            email="staff-webauthn@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self._activate_totp(user)
        Authenticator.objects.create(
            user=user,
            type=Authenticator.Type.WEBAUTHN,
            data={},
        )
        session = SessionStore()
        session[SESSION_KEY_ADMIN_MFA_PENDING_USER] = {
            "version": 1,
            "user_pk": str(user.pk),
            "started_at": time.time(),
            "next": "/admin/",
            "flow_id": "a" * 32,
        }
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key

        client_data = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "type": "webauthn.get",
                        "challenge": base64.urlsafe_b64encode(b"challenge")
                        .decode()
                        .rstrip("="),
                        "origin": "http://admin.localhost",
                    }
                ).encode()
            )
            .decode()
            .rstrip("=")
        )
        body = {
            "id": "credential",
            "rawId": "credential",
            "type": "public-key",
            "response": {"clientDataJSON": client_data},
        }

        challenge = base64.urlsafe_b64encode(b"challenge").decode().rstrip("=")

        def fake_begin(*, user):
            allauth_context.request.session[
                allauth_webauthn.STATE_SESSION_KEY
            ] = {
                "challenge": challenge,
                "user_verification": "preferred",
            }
            return {
                "publicKey": {
                    "challenge": challenge,
                    "userVerification": "preferred",
                }
            }

        with patch.object(
            allauth_webauthn,
            "begin_authentication",
            side_effect=fake_begin,
        ):
            options_response = self.client.get(
                "/admin/mfa-verify/webauthn-options/",
                HTTP_HOST="admin.localhost",
            )
        self.assertEqual(options_response.status_code, 200)

        with patch("backend.admin_site.logger.log") as log_mock:
            response = self.client.post(
                "/admin/mfa-verify/webauthn-complete/",
                data=json.dumps(body),
                content_type="application/json",
                HTTP_HOST="admin.localhost",
                HTTP_ORIGIN="http://admin.localhost",
            )

        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            response.content,
            {"error": "Verification failed"},
        )
        _mock_complete.assert_called_once()
        self.assertTrue(
            any(
                call.args[1] == "admin.mfa.failed"
                for call in log_mock.call_args_list
            )
        )
        self.assertTrue(
            any(
                call.kwargs["extra"]["event"] == "admin.mfa.failed"
                for call in log_mock.call_args_list
            )
        )
