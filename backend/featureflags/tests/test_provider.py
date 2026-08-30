from __future__ import annotations

from django.test import TestCase, override_settings
from openfeature.evaluation_context import EvaluationContext
from openfeature.flag_evaluation import ErrorCode, Reason

from featureflags.models import (
    FeatureDefinition,
    FeatureKind,
)
from featureflags.provider import DjangoAdminFeatureProvider


class DjangoAdminFeatureProviderTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.provider = DjangoAdminFeatureProvider()

    def test_resolve_string_details_from_staff_preview(self):
        feature, _ = FeatureDefinition.objects.update_or_create(
            key="site_itmocraft_page_version",
            defaults={
                "kind": FeatureKind.VARIANT,
                "default_value": "legacy",
            },
        )
        details = self.provider.resolve_string_details(
            "site_itmocraft_page_version",
            "legacy",
            evaluation_context=EvaluationContext(
                targeting_key="user:7",
                attributes={
                    "user_id": 7,
                    "is_staff": True,
                    "overrides": {
                        "site_itmocraft_page_version": "v2",
                    },
                },
            ),
        )

        self.assertEqual(details.value, "v2")
        self.assertEqual(details.reason, Reason.STATIC)
        self.assertEqual(details.variant, "v2")

    def test_resolve_boolean_details_reports_missing_flag(self):
        details = self.provider.resolve_boolean_details(
            "missing_flag",
            True,
        )

        self.assertTrue(details.value)
        self.assertEqual(details.reason, Reason.DEFAULT)
        self.assertEqual(details.error_code, ErrorCode.FLAG_NOT_FOUND)

    def test_missing_design_definition_uses_registry_fallback(self):
        FeatureDefinition.objects.filter(
            key="site_itmocraft_page_version"
        ).delete()

        details = self.provider.resolve_string_details(
            "site_itmocraft_page_version",
            "v2",
        )

        self.assertEqual(details.value, "legacy")
        self.assertEqual(details.reason, Reason.DEFAULT)
        self.assertEqual(details.variant, "legacy")

    def test_inactive_design_definition_uses_registry_fallback(self):
        feature, _ = FeatureDefinition.objects.update_or_create(
            key="site_itmocraft_page_version",
            defaults={
                "kind": FeatureKind.VARIANT,
                "default_value": "v2",
            },
        )
        feature.default_value = "v2"
        feature.active = False
        feature.save(update_fields=["default_value", "active"])

        details = self.provider.resolve_string_details(
            "site_itmocraft_page_version",
            "v2",
        )

        self.assertEqual(details.value, "legacy")
        self.assertEqual(details.reason, Reason.DEFAULT)
        self.assertEqual(details.variant, "legacy")

    @override_settings(FF_PROFILE_PERSONALIZATION_ENFORCE=False)
    def test_missing_boolean_definition_uses_registry_fallback(self):
        FeatureDefinition.objects.filter(
            key="profile_personalization_enforce"
        ).delete()

        details = self.provider.resolve_boolean_details(
            "profile_personalization_enforce",
            True,
        )

        self.assertFalse(details.value)
        self.assertEqual(details.reason, Reason.DEFAULT)
        self.assertEqual(details.variant, "False")

    @override_settings(FF_PROFILE_PERSONALIZATION_ENFORCE=False)
    def test_inactive_boolean_definition_uses_registry_fallback(self):
        feature, _ = FeatureDefinition.objects.update_or_create(
            key="profile_personalization_enforce",
            defaults={
                "kind": FeatureKind.BOOLEAN,
                "default_value": "true",
            },
        )
        feature.default_value = "true"
        feature.active = False
        feature.save(update_fields=["default_value", "active"])

        details = self.provider.resolve_boolean_details(
            "profile_personalization_enforce",
            True,
        )

        self.assertFalse(details.value)
        self.assertEqual(details.reason, Reason.DEFAULT)
        self.assertEqual(details.variant, "False")

    def test_resolve_boolean_details_reports_type_mismatch(self):
        FeatureDefinition.objects.update_or_create(
            key="site_itmocraft_page_version",
            defaults={
                "kind": FeatureKind.VARIANT,
                "default_value": "legacy",
            },
        )

        details = self.provider.resolve_boolean_details(
            "site_itmocraft_page_version",
            False,
        )

        self.assertFalse(details.value)
        self.assertEqual(details.reason, Reason.ERROR)
        self.assertEqual(details.error_code, ErrorCode.TYPE_MISMATCH)
