from __future__ import annotations

import json

from accounts.tests.base import APITestCase
from django.test.utils import override_settings
from featureflags.models import (
    FeatureDefinition,
    FeatureGroup,
    FeatureRule,
    FeatureRuleType,
)

from bff.schemas import PageDocument

DESIGN_FLAGS = {
    "site_itmocraft_page_version": "itmocraft",
    "site_joutak_page_version": "joutak",
    "site_minigames_page_version": "minigames",
    "site_header_version": "",
    "site_footer_version": "",
}


@override_settings(
    ACCOUNT_EMAIL_VERIFICATION="none",
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
        self.group, _ = FeatureGroup.objects.get_or_create(
            name="Website design testers",
            slug="website-design-testers",
        )
        self.group.members.clear()
        for key, page in DESIGN_FLAGS.items():
            feature = FeatureDefinition.objects.get(key=key)
            feature.default_value = "legacy"
            feature.active = True
            feature.sticky_assignment = False
            feature.save(
                update_fields=[
                    "default_value",
                    "active",
                    "sticky_assignment",
                ]
            )
            feature.rules.all().delete()
            feature.overrides.all().delete()
            FeatureRule.objects.create(
                feature=feature,
                name="Website design testers",
                priority=10,
                rule_type=FeatureRuleType.GROUP,
                value="v2",
                page=page,
                group_ids=[self.group.pk],
            )

    def get_page(self, endpoint="/bff/pages/itmocraft"):
        return self.client.get(endpoint, HTTP_HOST="api.localhost")

    def test_bootstrap_is_non_product_and_sets_anonymous_cookie(self):
        response = self.client.get("/bff/bootstrap", HTTP_HOST="api.localhost")

        self.assertEqual(response.status_code, 200)
        self.assertIn("viewer", response.json())
        self.assertNotIn("layout", response.json())
        self.assertIn("joutak_ffid", response.cookies)

    def test_removed_home_endpoint_returns_404(self):
        response = self.client.get(
            "/bff/pages/home",
            HTTP_HOST="api.localhost",
        )

        self.assertEqual(response.status_code, 404)

    def test_anonymous_product_response_is_legacy_and_valid(self):
        response = self.get_page()
        document = PageDocument.model_validate(response.json())

        self.assertEqual(document.product.id, "itmocraft")
        self.assertEqual(document.product.canonical_path, "/")
        self.assertEqual(document.effective_page_variant, "legacy")
        self.assertEqual(document.layout.header_variant, "legacy")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(
            response["Vary"],
            "Cookie, X-Session-Token, Origin",
        )

    def test_group_member_receives_v2_page_and_layout(self):
        user = self.create_legacy_user(email=self.unique_email("tester"))
        self.group.members.add(user)
        self.client.force_login(user)

        document = PageDocument.model_validate(self.get_page().json())

        self.assertEqual(document.effective_page_variant, "v2")
        self.assertEqual(document.variant_source, "feature_flag")
        self.assertEqual(document.layout.header_variant, "v2")
        self.assertEqual(document.layout.footer_variant, "v2")

    def test_v2_documents_preserve_primary_legacy_user_actions(self):
        user = self.create_legacy_user(email=self.unique_email("actions"))
        self.group.members.add(user)
        self.client.force_login(user)

        expected = {
            "/bff/pages/itmocraft": {
                "https://forms.yandex.ru/u/67773408068ff0452320c8b4/",
            },
            "/bff/pages/joutak": {
                "https://forms.yandex.ru/u/6501f64f43f74f18a8da28de/",
                "/joutak/pay",
                "mc.joutak.ru",
            },
            "/bff/pages/minigames": {
                "https://vk.me/join/WDyZMd4pF8Xhu/egqaDnrHmbajAmm0cZ2og=",
                (
                    "https://docs.google.com/forms/d/e/"
                    "1FAIpQLSfX7C2f1WII6Ak_me3onbRAcb71MSEap51MS-"
                    "Hic4XYg915MA/viewform"
                ),
                (
                    "https://docs.google.com/document/d/"
                    "1TasKKNFDkostGTnX0SsSpCzvgKw7tITA/edit?tab=t.0"
                ),
                "https://vk.com/kb_esports",
                "craft.itmo.ru",
            },
        }

        for endpoint, expected_values in expected.items():
            with self.subTest(endpoint=endpoint):
                document = PageDocument.model_validate(
                    self.get_page(endpoint).json()
                )
                payload = document.content.model_dump_json()
                for value in expected_values:
                    self.assertIn(value, payload)

    def test_itmocraft_alias_keeps_legacy_body_but_independent_layout(self):
        user = self.create_legacy_user(email=self.unique_email("alias"))
        self.group.members.add(user)
        self.client.force_login(user)

        response = self.get_page("/bff/pages/itmocraft/legacy")
        document = PageDocument.model_validate(response.json())

        self.assertEqual(document.effective_page_variant, "legacy")
        self.assertEqual(document.variant_source, "fixed_legacy")
        self.assertTrue(document.product.is_legacy_alias)
        self.assertEqual(document.product.requested_path, "/itmocraft")
        self.assertEqual(document.layout.header_variant, "v2")
        self.assertEqual(document.layout.footer_variant, "v2")

    def test_get_query_cannot_mutate_preview_cookie(self):
        response = self.client.get(
            "/bff/bootstrap",
            {"ff_site_header_version": "v2"},
            HTTP_HOST="api.localhost",
        )

        self.assertNotIn("joutak_ff_override", response.cookies)

    def test_staff_can_set_and_delete_preview_with_unsafe_methods(self):
        staff = self.create_legacy_user(email=self.unique_email("staff"))
        staff.is_staff = True
        staff.save(update_fields=["is_staff"])
        self.client.force_login(staff)

        response = self.client.post(
            "/bff/feature-overrides",
            data=json.dumps(
                {
                    "overrides": {
                        "site_itmocraft_page_version": "v2",
                        "site_header_version": "v2",
                    }
                }
            ),
            content_type="application/json",
            HTTP_HOST="api.localhost",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("joutak_ff_override", response.cookies)
        self.assertEqual(
            self.get_page().json()["effective_page_variant"],
            "v2",
        )

        response = self.client.delete(
            "/bff/feature-overrides",
            HTTP_HOST="api.localhost",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies["joutak_ff_override"]["max-age"], 0)

    def test_account_summary_requires_authentication(self):
        response = self.client.get(
            "/bff/account/summary",
            HTTP_HOST="api.localhost",
        )
        self.assertEqual(response.status_code, 401)

        user = self.create_legacy_user(email=self.unique_email("account"))
        self.client.force_login(user)
        response = self.client.get(
            "/bff/account/summary",
            HTTP_HOST="api.localhost",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["viewer"]["is_authenticated"])
