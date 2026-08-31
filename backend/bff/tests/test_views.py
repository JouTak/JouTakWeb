from __future__ import annotations

import json
from unittest.mock import patch

from accounts.services.auth import AuthService
from accounts.tests.base import APITestCase
from django.test.utils import override_settings
from featureflags.models import (
    FeatureDefinition,
    FeatureGroup,
    FeatureKind,
    FeatureRule,
    FeatureRuleType,
)
from featureflags.services import evaluate_many

from bff.schemas import PageDocument

DESIGN_FLAGS = {
    "site_itmocraft_page_version": "itmocraft",
    "site_joutak_page_version": "joutak",
    "site_minigames_page_version": "minigames",
    "site_contact_page_version": "contact",
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

    def get_contact(self):
        return self.get_page("/bff/pages/contact")

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

    def test_anonymous_contact_response_is_legacy_and_valid(self):
        response = self.get_contact()
        document = PageDocument.model_validate(response.json())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(document.product.id, "contact")
        self.assertEqual(document.product.canonical_path, "/contact")
        self.assertEqual(document.product.requested_path, "/contact")
        self.assertFalse(document.product.is_legacy_alias)
        self.assertEqual(document.effective_page_variant, "legacy")
        self.assertEqual(document.variant_source, "default")
        self.assertEqual(document.layout.header_variant, "legacy")
        self.assertEqual(document.layout.footer_variant, "legacy")
        self.assertEqual(document.layout.default_project, "jou_tak")
        self.assertEqual(document.content.template, "landing-legacy")
        self.assertEqual(document.content.sections, [])
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(
            response["Vary"],
            "Cookie, X-Session-Token, Origin",
        )
        self.assertIn("joutak_ffid", response.cookies)

    def test_authenticated_non_tester_receives_legacy_contact(self):
        user = self.create_legacy_user(email=self.unique_email("ordinary"))
        self.client.force_login(user)

        document = PageDocument.model_validate(self.get_contact().json())

        self.assertEqual(document.effective_page_variant, "legacy")
        self.assertEqual(document.variant_source, "default")

    def test_public_rule_serves_v2_contact_to_all_visitors(self):
        feature = FeatureDefinition.objects.get(
            key="site_contact_page_version"
        )
        feature.rules.all().delete()
        FeatureRule.objects.create(
            feature=feature,
            name="Public contact page",
            priority=10,
            rule_type=FeatureRuleType.EVERYONE,
            value="v2",
            page="contact",
        )

        anonymous_document = PageDocument.model_validate(
            self.get_contact().json()
        )
        user = self.create_legacy_user(
            email=self.unique_email("public-contact")
        )
        self.client.force_login(user)
        authenticated_document = PageDocument.model_validate(
            self.get_contact().json()
        )

        for document in (anonymous_document, authenticated_document):
            self.assertEqual(document.effective_page_variant, "v2")
            self.assertEqual(document.variant_source, "feature_flag")
            self.assertEqual(document.content.template, "landing-v2")

    def test_design_tester_receives_v2_contact(self):
        user = self.create_legacy_user(
            email=self.unique_email("contact-tester")
        )
        self.group.members.add(user)
        self.client.force_login(user)

        document = PageDocument.model_validate(self.get_contact().json())

        self.assertEqual(document.effective_page_variant, "v2")
        self.assertEqual(document.variant_source, "feature_flag")
        self.assertEqual(document.layout.header_variant, "v2")
        self.assertEqual(document.layout.footer_variant, "v2")
        self.assertEqual(document.content.template, "landing-v2")

    def test_staff_preview_can_select_v2_contact(self):
        staff = self.create_legacy_user(
            email=self.unique_email("contact-staff")
        )
        staff.is_staff = True
        staff.save(update_fields=["is_staff"])
        self.client.force_login(staff)

        preview_response = self.client.post(
            "/bff/feature-overrides",
            data=json.dumps(
                {
                    "overrides": {
                        "site_contact_page_version": "v2",
                    }
                }
            ),
            content_type="application/json",
            HTTP_HOST="api.localhost",
        )
        document = PageDocument.model_validate(self.get_contact().json())

        self.assertEqual(preview_response.status_code, 200)
        self.assertEqual(document.effective_page_variant, "v2")
        self.assertEqual(document.variant_source, "staff_preview")

    def test_invalid_or_unavailable_contact_flag_fails_closed(self):
        feature = FeatureDefinition.objects.get(
            key="site_contact_page_version"
        )

        FeatureDefinition.objects.filter(pk=feature.pk).update(
            default_value="invalid"
        )
        invalid_document = PageDocument.model_validate(
            self.get_contact().json()
        )

        FeatureDefinition.objects.filter(pk=feature.pk).update(
            default_value="legacy",
            active=False,
        )
        unavailable_document = PageDocument.model_validate(
            self.get_contact().json()
        )

        for document in (invalid_document, unavailable_document):
            self.assertEqual(document.effective_page_variant, "legacy")
            self.assertEqual(document.variant_source, "default")

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

    def test_invalid_preview_does_not_expose_exception_details(self):
        staff = self.create_legacy_user(
            email=self.unique_email("staff-invalid-preview")
        )
        staff.is_staff = True
        staff.save(update_fields=["is_staff"])
        self.client.force_login(staff)
        internal_detail = "failed at /srv/joutak/backend/featureflags.py:42"

        with patch(
            "bff.views.set_override_cookie",
            side_effect=ValueError(internal_detail),
        ):
            response = self.client.post(
                "/bff/feature-overrides",
                data=json.dumps(
                    {
                        "overrides": {
                            "site_itmocraft_page_version": "v2",
                        }
                    }
                ),
                content_type="application/json",
                HTTP_HOST="api.localhost",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"detail": "Invalid feature override request."},
        )
        self.assertNotIn(internal_detail, response.content.decode())

    def test_preview_rejects_non_object_json(self):
        staff = self.create_legacy_user(
            email=self.unique_email("staff-invalid-json-shape")
        )
        staff.is_staff = True
        staff.save(update_fields=["is_staff"])
        self.client.force_login(staff)

        response = self.client.post(
            "/bff/feature-overrides",
            data="[]",
            content_type="application/json",
            HTTP_HOST="api.localhost",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"detail": "Invalid feature override request."},
        )

    def test_staff_preview_for_one_key_does_not_unlock_another(self):
        staff = self.create_legacy_user(email=self.unique_email("staff-key"))
        staff.is_staff = True
        staff.save(update_fields=["is_staff"])
        self.client.force_login(staff)
        page_feature = FeatureDefinition.objects.get(
            key="site_itmocraft_page_version"
        )
        page_feature.rules.all().delete()
        FeatureRule.objects.create(
            feature=page_feature,
            name="unsafe-everyone-v2",
            priority=10,
            rule_type=FeatureRuleType.EVERYONE,
            value="v2",
            page="itmocraft",
        )

        response = self.client.post(
            "/bff/feature-overrides",
            data=json.dumps({"overrides": {"site_header_version": "v2"}}),
            content_type="application/json",
            HTTP_HOST="api.localhost",
        )
        self.assertEqual(response.status_code, 200)

        document = PageDocument.model_validate(self.get_page().json())
        self.assertEqual(document.effective_page_variant, "legacy")
        self.assertEqual(document.variant_source, "default")
        self.assertEqual(document.layout.header_variant, "v2")

    def test_page_preview_does_not_unlock_header_or_footer(self):
        staff = self.create_legacy_user(
            email=self.unique_email("staff-layout-key")
        )
        staff.is_staff = True
        staff.save(update_fields=["is_staff"])
        self.client.force_login(staff)
        for key in ("site_header_version", "site_footer_version"):
            feature = FeatureDefinition.objects.get(key=key)
            feature.rules.all().delete()
            FeatureRule.objects.create(
                feature=feature,
                name="unsafe-everyone-v2",
                priority=10,
                rule_type=FeatureRuleType.EVERYONE,
                value="v2",
            )

        response = self.client.post(
            "/bff/feature-overrides",
            data=json.dumps(
                {
                    "overrides": {
                        "site_itmocraft_page_version": "v2",
                    }
                }
            ),
            content_type="application/json",
            HTTP_HOST="api.localhost",
        )
        self.assertEqual(response.status_code, 200)

        document = PageDocument.model_validate(self.get_page().json())
        self.assertEqual(document.effective_page_variant, "v2")
        self.assertEqual(document.variant_source, "staff_preview")
        self.assertEqual(document.layout.header_variant, "legacy")
        self.assertEqual(document.layout.footer_variant, "legacy")

    def test_account_summary_reuses_one_feature_snapshot_for_viewer(self):
        user = self.create_legacy_user(email=self.unique_email("snapshot"))
        self.client.force_login(user)
        feature, _ = FeatureDefinition.objects.get_or_create(
            key="profile_personalization_ui",
            defaults={
                "kind": FeatureKind.BOOLEAN,
                "default_value": "true",
            },
        )
        feature.kind = FeatureKind.BOOLEAN
        feature.default_value = "true"
        feature.active = True
        feature.save(update_fields=["kind", "default_value", "active"])
        feature.rules.all().delete()
        FeatureRule.objects.create(
            feature=feature,
            name="everyone-off",
            priority=10,
            rule_type=FeatureRuleType.EVERYONE,
            value="false",
        )

        with (
            patch(
                "bff.services.evaluate_many",
                wraps=evaluate_many,
            ) as bff_evaluate,
            patch(
                "accounts.services.account_status.evaluate_many",
                wraps=evaluate_many,
            ) as account_evaluate,
            patch(
                "bff.services.AuthService.profile",
                wraps=AuthService.profile,
            ) as profile,
        ):
            response = self.client.get(
                "/bff/account/summary",
                HTTP_HOST="api.localhost",
            )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            response.json()["features"]["profile_personalization_ui"]
        )
        self.assertEqual(bff_evaluate.call_count, 1)
        self.assertEqual(account_evaluate.call_count, 0)
        self.assertFalse(
            profile.call_args.kwargs["feature_decisions"][
                "profile_personalization_ui"
            ]
        )

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
