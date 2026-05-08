from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from featureflags.models import (
    ExperimentAssignment,
    FeatureDefinition,
    FeatureGroup,
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

    def test_authenticated_user_identity_overrides_anonymous_default(
        self,
    ):
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

    # ─── Denylist Tests ──────────────────────────────────────────────

    def test_user_denylist_forces_default_value(self):
        """User in denylist gets the feature default, not the rule value."""
        user = User.objects.create_user(
            username="denied-user",
            email="denied@example.com",
            password="StrongPass123!",
        )
        feature = self.homepage_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="deny-user",
            priority=5,
            rule_type=FeatureRuleType.USER_DENYLIST,
            value="v2",
            actor_ids=[str(user.pk)],
        )
        FeatureRule.objects.create(
            feature=feature,
            name="everyone-v2",
            priority=10,
            rule_type=FeatureRuleType.EVERYONE,
            value="v2",
        )

        decisions = evaluate_many(
            RequestEvaluationContext(user=user, anonymous_id="anon"),
            ["site_homepage_version"],
        )
        self.assertEqual(decisions["site_homepage_version"], "legacy")

    def test_anonymous_denylist_forces_default_value(self):
        """Anonymous user in denylist gets the feature default."""
        feature = self.homepage_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="deny-anon",
            priority=5,
            rule_type=FeatureRuleType.ANONYMOUS_DENYLIST,
            value="v2",
            actor_ids=["blocked-anon-id"],
        )
        FeatureRule.objects.create(
            feature=feature,
            name="everyone-v2",
            priority=10,
            rule_type=FeatureRuleType.EVERYONE,
            value="v2",
        )

        decisions = evaluate_many(
            RequestEvaluationContext(anonymous_id="blocked-anon-id"),
            ["site_homepage_version"],
        )
        self.assertEqual(decisions["site_homepage_version"], "legacy")

    # ─── Group Targeting Tests ───────────────────────────────────────

    def test_group_rule_matches_member(self):
        """User who is member of a target group gets the rule value."""
        user = User.objects.create_user(
            username="group-member",
            email="group-member@example.com",
            password="StrongPass123!",
        )
        group = FeatureGroup.objects.create(
            name="Beta Testers", slug="beta-testers"
        )
        group.members.add(user)

        feature = self.homepage_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="beta-v2",
            priority=10,
            rule_type=FeatureRuleType.GROUP,
            value="v2",
            group_ids=[group.pk],
        )

        decisions = evaluate_many(
            RequestEvaluationContext(user=user, anonymous_id="anon"),
            ["site_homepage_version"],
        )
        self.assertEqual(decisions["site_homepage_version"], "v2")

    def test_group_rule_does_not_match_non_member(self):
        """User not in the target group does not get the rule value."""
        user = User.objects.create_user(
            username="non-member",
            email="non-member@example.com",
            password="StrongPass123!",
        )
        group = FeatureGroup.objects.create(name="VIP Users", slug="vip-users")
        # user is NOT added to the group

        feature = self.homepage_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="vip-v2",
            priority=10,
            rule_type=FeatureRuleType.GROUP,
            value="v2",
            group_ids=[group.pk],
        )

        decisions = evaluate_many(
            RequestEvaluationContext(user=user, anonymous_id="anon"),
            ["site_homepage_version"],
        )
        self.assertEqual(decisions["site_homepage_version"], "legacy")

    def test_group_rule_does_not_match_anonymous(self):
        """Anonymous users never match group rules."""
        group = FeatureGroup.objects.create(
            name="Staff Group", slug="staff-group"
        )
        feature = self.homepage_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="group-v2",
            priority=10,
            rule_type=FeatureRuleType.GROUP,
            value="v2",
            group_ids=[group.pk],
        )

        decisions = evaluate_many(
            RequestEvaluationContext(anonymous_id="anon-visitor"),
            ["site_homepage_version"],
        )
        self.assertEqual(decisions["site_homepage_version"], "legacy")

    # ─── Disabled Rules / Inactive Features ──────────────────────────

    def test_disabled_rule_is_skipped(self):
        """A rule with enabled=False should not match."""
        feature = self.homepage_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="disabled-rule",
            priority=5,
            rule_type=FeatureRuleType.EVERYONE,
            value="v2",
            enabled=False,
        )

        decisions = evaluate_many(
            RequestEvaluationContext(anonymous_id="anon"),
            ["site_homepage_version"],
        )
        self.assertEqual(decisions["site_homepage_version"], "legacy")

    def test_inactive_feature_returns_default(self):
        """A feature with active=False is not loaded."""
        feature = self.homepage_feature()
        feature.active = False
        feature.save(update_fields=["active"])
        FeatureRule.objects.create(
            feature=feature,
            name="everyone-v2",
            priority=10,
            rule_type=FeatureRuleType.EVERYONE,
            value="v2",
        )

        decisions = evaluate_many(
            RequestEvaluationContext(anonymous_id="anon"),
            ["site_homepage_version"],
        )
        # Falls through to DEFAULT_FEATURES since DB feature is inactive
        self.assertEqual(decisions["site_homepage_version"], "legacy")

    # ─── Page-Scoped Rules ───────────────────────────────────────────

    def test_page_scoped_rule_only_matches_matching_page(self):
        """A rule with page='homepage' only matches that page context."""
        feature = self.homepage_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="homepage-only-v2",
            priority=10,
            rule_type=FeatureRuleType.EVERYONE,
            value="v2",
            page="homepage",
        )

        homepage_ctx = RequestEvaluationContext(
            anonymous_id="anon", page="homepage"
        )
        other_ctx = RequestEvaluationContext(
            anonymous_id="anon", page="account"
        )

        homepage_result = evaluate_many(
            homepage_ctx, ["site_homepage_version"]
        )
        other_result = evaluate_many(other_ctx, ["site_homepage_version"])

        self.assertEqual(homepage_result["site_homepage_version"], "v2")
        self.assertEqual(other_result["site_homepage_version"], "legacy")

    # ─── Sticky Assignment Tests ─────────────────────────────────────

    def test_sticky_assignment_persists_and_reuses(self):
        """Once assigned, sticky assignment is returned on next eval."""
        feature = self.homepage_feature()
        feature.sticky_assignment = True
        feature.save(update_fields=["sticky_assignment"])
        FeatureRule.objects.create(
            feature=feature,
            name="everyone-v2",
            priority=10,
            rule_type=FeatureRuleType.EVERYONE,
            value="v2",
        )

        context = RequestEvaluationContext(anonymous_id="sticky-user", page="")
        first = evaluate_many(context, ["site_homepage_version"])
        self.assertEqual(first["site_homepage_version"], "v2")

        # Verify assignment was persisted
        assignment = ExperimentAssignment.objects.get(
            feature=feature, subject_key="sticky-user"
        )
        self.assertEqual(assignment.value, "v2")

        # Now delete the rule — sticky value should still be returned
        feature.rules.all().delete()
        second = evaluate_many(context, ["site_homepage_version"])
        self.assertEqual(second["site_homepage_version"], "v2")

    # ─── Batch Evaluation Tests ──────────────────────────────────────

    def test_batch_evaluation_loads_multiple_features(self):
        """evaluate_many handles multiple keys in a single call."""
        FeatureDefinition.objects.create(
            key="flag_alpha",
            kind=FeatureKind.BOOLEAN,
            default_value="true",
        )
        feature_b = FeatureDefinition.objects.create(
            key="flag_beta",
            kind=FeatureKind.BOOLEAN,
            default_value="false",
        )
        FeatureRule.objects.create(
            feature=feature_b,
            name="everyone-on",
            priority=10,
            rule_type=FeatureRuleType.EVERYONE,
            value="true",
        )

        decisions = evaluate_many(
            RequestEvaluationContext(anonymous_id="multi"),
            ["flag_alpha", "flag_beta", "missing_flag"],
        )

        self.assertEqual(decisions["flag_alpha"], True)
        self.assertEqual(decisions["flag_beta"], True)
        self.assertEqual(decisions["missing_flag"], False)
