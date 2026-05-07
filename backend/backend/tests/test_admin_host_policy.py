from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

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
        self.assertContains(
            response,
            "authenticator app code or passkey",
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
    def test_staff_without_mfa_is_denied(self, _mocked):
        user = User.objects.create_user(
            username="staff_no_mfa",
            email="staff-no-mfa@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get("/admin/", HTTP_HOST="admin.localhost")

        self.assertEqual(response.status_code, 403)

    @patch("backend.middleware.admin_mfa_is_enabled", return_value=True)
    def test_staff_with_mfa_can_access_admin(self, _mocked):
        user = User.objects.create_user(
            username="staff_yes_mfa",
            email="staff-yes-mfa@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get("/admin/", HTTP_HOST="admin.localhost")

        self.assertEqual(response.status_code, 200)

    @patch("backend.middleware.admin_mfa_is_enabled", return_value=True)
    def test_staff_can_open_registered_backoffice_models(self, _mocked):
        user = User.objects.create_user(
            username="staff_models",
            email="staff-models@example.com",
            password="StrongPass123!",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(user)

        for path in (
            "/admin/auth/user/",
            "/admin/core/userprofile/",
            "/admin/core/usersessionmeta/",
            "/admin/featureflags/featuredefinition/",
        ):
            response = self.client.get(path, HTTP_HOST="admin.localhost")
            self.assertEqual(response.status_code, 200, path)
