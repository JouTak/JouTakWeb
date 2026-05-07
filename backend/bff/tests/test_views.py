from __future__ import annotations

from accounts.tests.base import APITestCase
from django.test.utils import override_settings
from featureflags.models import (
    FeatureDefinition,
    FeatureKind,
    FeatureRule,
    FeatureRuleType,
)


@override_settings(
    FEATURE_FLAG_OVERRIDE_QUERY_ENABLED=True,
    DJANGO_ALLOWED_HOSTS=(
        "localhost",
        "127.0.0.1",
        "api.localhost",
        "admin.localhost",
    ),
    DJANGO_API_HOSTS=("api.localhost",),
    DJANGO_ADMIN_HOSTS=("admin.localhost",),
)
class BffViewTests(APITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.feature, _created = FeatureDefinition.objects.get_or_create(
            key="site_homepage_version",
            defaults={
                "kind": FeatureKind.VARIANT,
                "default_value": "legacy",
            },
        )
        self.feature.kind = FeatureKind.VARIANT
        self.feature.default_value = "legacy"
        self.feature.save(update_fields=["kind", "default_value"])
        self.feature.rules.all().delete()
        self.feature.overrides.all().delete()
        self.feature.assignments.all().delete()
        FeatureRule.objects.create(
            feature=self.feature,
            name="staff-v2",
            priority=10,
            rule_type=FeatureRuleType.STAFF,
            value="v2",
        )

    def test_bootstrap_sets_anonymous_cookie_and_returns_feature_payload(self):
        response = self.client.get("/bff/bootstrap", HTTP_HOST="api.localhost")

        self.assertEqual(response.status_code, 200)
        self.assertIn("viewer", response.json())
        self.assertIn("features", response.json())
        self.assertIn("joutak_ffid", response.cookies)
        self.assertNotIn("identity_key", response.json()["experiments"])

    def test_homepage_override_persists_via_cookie(self):
        bootstrap_response = self.client.get(
            "/bff/bootstrap",
            {"ff_site_homepage_version": "v2"},
            HTTP_HOST="api.localhost",
        )
        self.assertEqual(bootstrap_response.status_code, 200)
        self.assertIn("joutak_ff_override", bootstrap_response.cookies)

        response = self.client.get(
            "/bff/pages/home", HTTP_HOST="api.localhost"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["variant"], "v2")

    def test_account_summary_returns_authenticated_viewer(self):
        auth = self.signup_and_auth()
        response = self.client.get(
            "/bff/account/summary",
            HTTP_HOST="api.localhost",
            **self.auth_headers(auth["session_token"]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["viewer"]["is_authenticated"])

    def test_api_host_keeps_home_bff_available(self):
        response = self.client.get(
            "/bff/pages/home", HTTP_HOST="api.localhost"
        )

        self.assertEqual(response.status_code, 200)
