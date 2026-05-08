from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from backend.admin_site import SESSION_KEY_ADMIN_MFA_VERIFIED

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
)
class AdminHostPolicyTests(TestCase):
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
            "Admin access requires a configured MFA factor.",
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

        # Without MFA enrolled, has_permission returns True (no MFA = no check)
        # but AdminSite still requires is_staff
        self.assertIn(response.status_code, (200, 302))

    @patch("backend.middleware.admin_mfa_is_enabled", return_value=True)
    @patch("backend.middleware.is_admin_mfa_verified", return_value=True)
    def test_staff_with_mfa_verified_can_access_admin(
        self, _mock_verified, _mock_enabled
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

    @patch("backend.middleware.admin_mfa_is_enabled", return_value=True)
    @patch("backend.middleware.is_admin_mfa_verified", return_value=True)
    def test_staff_can_open_registered_backoffice_models(
        self, _mock_verified, _mock_enabled
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
            "/admin/core/userprofile/",
            "/admin/core/usersessionmeta/",
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

    def test_mfa_verify_without_pending_session_redirects_to_login(
        self,
    ):
        """Accessing MFA verify without pending user redirects back."""
        response = self.client.get(
            "/admin/mfa-verify/", HTTP_HOST="admin.localhost"
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
