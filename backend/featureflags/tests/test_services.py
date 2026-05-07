from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from featureflags.models import (
    FeatureDefinition,
    FeatureKind,
    FeatureOverride,
    FeatureOverrideScope,
    FeatureRule,
    FeatureRuleType,
)
from featureflags.services import RequestEvaluationContext, evaluate_many

User = get_user_model()


class FeatureFlagServiceTests(TestCase):
    def homepage_feature(self) -> FeatureDefinition:
        feature, _created = FeatureDefinition.objects.get_or_create(
            key="site_homepage_version",
            defaults={
                "kind": FeatureKind.VARIANT,
                "default_value": "legacy",
            },
        )
        feature.kind = FeatureKind.VARIANT
        feature.default_value = "legacy"
        feature.save(update_fields=["kind", "default_value"])
        feature.rules.all().delete()
        feature.overrides.all().delete()
        feature.assignments.all().delete()
        return feature

    def test_returns_default_when_feature_missing(self):
        decisions = evaluate_many(
            RequestEvaluationContext(anonymous_id="anon-a"),
            ["unknown_flag"],
        )
        self.assertEqual(decisions["unknown_flag"], False)

    def test_request_override_has_highest_priority(self):
        feature = self.homepage_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="everyone-v2",
            priority=10,
            rule_type=FeatureRuleType.EVERYONE,
            value="v2",
        )
        FeatureOverride.objects.create(
            feature=feature,
            scope_type=FeatureOverrideScope.GLOBAL,
            value="legacy",
        )

        decisions = evaluate_many(
            RequestEvaluationContext(
                anonymous_id="anon-a",
                request_overrides={"site_homepage_version": "v2"},
            ),
            ["site_homepage_version"],
        )

        self.assertEqual(decisions["site_homepage_version"], "v2")

    def test_percentage_rollout_is_stable_for_same_identity(self):
        feature = FeatureDefinition.objects.create(
            key="homepage_percentage",
            kind=FeatureKind.VARIANT,
            default_value="legacy",
        )
        FeatureRule.objects.create(
            feature=feature,
            name="half-rollout",
            priority=10,
            rule_type=FeatureRuleType.PERCENTAGE,
            value="v2",
            percentage=50,
        )

        context = RequestEvaluationContext(
            anonymous_id="anon-fixed",
            page="homepage",
        )
        first = evaluate_many(context, ["homepage_percentage"])
        second = evaluate_many(context, ["homepage_percentage"])

        self.assertEqual(
            first["homepage_percentage"],
            second["homepage_percentage"],
        )

    def test_authenticated_user_identity_overrides_anonymous_default(self):
        user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="StrongPass123!",
        )
        feature = self.homepage_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="specific-user",
            priority=10,
            rule_type=FeatureRuleType.USER_ALLOWLIST,
            value="v2",
            actor_ids=[str(user.pk)],
        )

        anonymous = evaluate_many(
            RequestEvaluationContext(anonymous_id="anon-before-login"),
            ["site_homepage_version"],
        )
        authenticated = evaluate_many(
            RequestEvaluationContext(
                user=user,
                anonymous_id="anon-before-login",
            ),
            ["site_homepage_version"],
        )

        self.assertEqual(anonymous["site_homepage_version"], "legacy")
        self.assertEqual(authenticated["site_homepage_version"], "v2")

    def test_user_override_wins_over_matching_rule(self):
        user = User.objects.create_user(
            username="override-user",
            email="override@example.com",
            password="StrongPass123!",
        )
        feature = self.homepage_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="everyone-v2",
            priority=10,
            rule_type=FeatureRuleType.EVERYONE,
            value="v2",
        )
        FeatureOverride.objects.create(
            feature=feature,
            scope_type=FeatureOverrideScope.USER,
            scope_value=str(user.pk),
            value="legacy",
        )

        decisions = evaluate_many(
            RequestEvaluationContext(user=user, anonymous_id="anon-user"),
            ["site_homepage_version"],
        )

        self.assertEqual(decisions["site_homepage_version"], "legacy")
