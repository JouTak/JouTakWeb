from __future__ import annotations

from io import StringIO

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings


class EmailDeploySettingsTests(SimpleTestCase):
    def test_headless_frontend_urls_cover_confirmation_and_reset(self) -> None:
        urls = settings.HEADLESS_FRONTEND_URLS
        self.assertIn("account_confirm_email", urls)
        self.assertIn("account_reset_password", urls)
        self.assertIn("account_reset_password_from_key", urls)
        self.assertIn(
            "/confirm-email?key={key}",
            urls["account_confirm_email"],
        )
        self.assertTrue(
            urls["account_reset_password"].endswith("/reset-password")
        )
        self.assertIn(
            "/reset-password?key={key}",
            urls["account_reset_password_from_key"],
        )

    def test_cors_headers_allow_allauth_headless_email_headers(self) -> None:
        headers = {header.lower() for header in settings.CORS_ALLOW_HEADERS}
        self.assertIn("x-email-verification-key", headers)
        self.assertIn("x-password-reset-key", headers)


class EmailDeployRoutesTests(TestCase):
    def test_allauth_headless_verify_email_route_is_available(self) -> None:
        response = self.client.get("/api/auth/flow/app/v1/auth/email/verify")
        self.assertEqual(response.status_code, 400)

    def test_allauth_headless_password_reset_route_is_available(self) -> None:
        response = self.client.get("/api/auth/flow/app/v1/auth/password/reset")
        self.assertEqual(response.status_code, 400)


class SyncSiteCommandTests(TestCase):
    @override_settings(
        SITE_ID=1,
        SITE_DOMAIN="",
        SITE_NAME="JouTak",
        FRONTEND_BASE_URL="https://joutak.ru",
    )
    def test_sync_site_uses_frontend_domain_and_configured_name(self) -> None:
        Site.objects.update_or_create(
            id=1,
            defaults={"domain": "example.com", "name": "example.com"},
        )

        stdout = StringIO()
        call_command("sync_site", stdout=stdout)

        site = Site.objects.get(id=1)
        self.assertEqual(site.domain, "joutak.ru")
        self.assertEqual(site.name, "JouTak")
        self.assertIn(
            "Site(id=1, domain=joutak.ru, name=JouTak)",
            stdout.getvalue(),
        )
