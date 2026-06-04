from __future__ import annotations

from django.test import TestCase
from openfeature.evaluation_context import EvaluationContext
from openfeature.flag_evaluation import ErrorCode, Reason

from featureflags.models import (
    FeatureDefinition,
    FeatureKind,
    FeatureRule,
    FeatureRuleType,
)
from featureflags.provider import DjangoAdminFeatureProvider


class DjangoAdminFeatureProviderTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.provider = DjangoAdminFeatureProvider()

    def test_resolve_string_details_from_targeting_rule(self):
        feature = FeatureDefinition.objects.create(
            key="provider_homepage_variant",
            kind=FeatureKind.VARIANT,
            default_value="legacy",
        )
        FeatureRule.objects.create(
            feature=feature,
            name="staff-v2",
            priority=10,
            rule_type=FeatureRuleType.STAFF,
            value="v2",
        )

        details = self.provider.resolve_string_details(
            "provider_homepage_variant",
            "legacy",
            evaluation_context=EvaluationContext(
                targeting_key="user:7",
                attributes={"user_id": 7, "is_staff": True},
            ),
        )

        self.assertEqual(details.value, "v2")
        self.assertEqual(details.reason, Reason.TARGETING_MATCH)
        self.assertEqual(details.variant, "v2")

    def test_resolve_boolean_details_reports_missing_flag(self):
        details = self.provider.resolve_boolean_details(
            "missing_flag",
            False,
        )

        self.assertFalse(details.value)
        self.assertEqual(details.reason, Reason.DEFAULT)
        self.assertEqual(details.error_code, ErrorCode.FLAG_NOT_FOUND)

    def test_resolve_boolean_details_reports_type_mismatch(self):
        FeatureDefinition.objects.create(
            key="provider_homepage_variant_mismatch",
            kind=FeatureKind.VARIANT,
            default_value="legacy",
        )

        details = self.provider.resolve_boolean_details(
            "provider_homepage_variant_mismatch",
            False,
        )

        self.assertFalse(details.value)
        self.assertEqual(details.reason, Reason.ERROR)
        self.assertEqual(details.error_code, ErrorCode.TYPE_MISMATCH)
