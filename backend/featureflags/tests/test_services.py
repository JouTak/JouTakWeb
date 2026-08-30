from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

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
from featureflags.registry import (
    DESIGN_FLAG_KEYS,
    DESIGN_ROLLOUT_POLICY,
    DESIGN_TESTER_GROUP_SLUG,
    FEATURE_REGISTRY,
)
from featureflags.services import RequestEvaluationContext, evaluate_many

User = get_user_model()


class FeatureFlagServiceTests(TestCase):
    def itmocraft_feature(self) -> FeatureDefinition:
        feature = FeatureDefinition.objects.get_or_create(
            key="site_itmocraft_page_version",
            defaults={
                "kind": FeatureKind.VARIANT,
                "default_value": "legacy",
            },
        )[0]
        feature.kind = FeatureKind.VARIANT
        feature.default_value = "legacy"
        feature.save(update_fields=["kind", "default_value"])
        feature.rules.all().delete()
        feature.overrides.all().delete()
        feature.assignments.all().delete()
        return feature

    def boolean_feature(self) -> FeatureDefinition:
        feature = FeatureDefinition.objects.get_or_create(
            key="profile_personalization_ui",
            defaults={
                "kind": FeatureKind.BOOLEAN,
                "default_value": "false",
            },
        )[0]
        feature.kind = FeatureKind.BOOLEAN
        feature.default_value = "false"
        feature.active = True
        feature.sticky_assignment = False
        feature.save(
            update_fields=[
                "kind",
                "default_value",
                "active",
                "sticky_assignment",
            ]
        )
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

    @override_settings(FF_PROFILE_PERSONALIZATION_ENFORCE=False)
    def test_invalid_stored_default_uses_registry_fallback(self):
        feature, _ = FeatureDefinition.objects.get_or_create(
            key="profile_personalization_enforce",
            defaults={
                "kind": FeatureKind.BOOLEAN,
                "default_value": "garbage",
            },
        )
        feature.kind = FeatureKind.BOOLEAN
        feature.default_value = "garbage"
        feature.active = True
        feature.save(update_fields=["kind", "default_value", "active"])
        feature.rules.all().delete()
        feature.overrides.all().delete()

        decisions = evaluate_many(
            RequestEvaluationContext(anonymous_id="invalid-default"),
            ["profile_personalization_enforce"],
        )

        self.assertFalse(decisions["profile_personalization_enforce"])

    def test_request_override_has_highest_priority(self):
        staff = User.objects.create_user(
            username="preview-staff",
            email="preview-staff@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        feature = self.itmocraft_feature()
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
                user=staff,
                anonymous_id="anon-a",
                request_overrides={"site_itmocraft_page_version": "v2"},
            ),
            ["site_itmocraft_page_version"],
        )

        self.assertEqual(decisions["site_itmocraft_page_version"], "v2")

    def test_design_request_override_requires_staff(self):
        feature = self.itmocraft_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="everyone-v2",
            priority=10,
            rule_type=FeatureRuleType.EVERYONE,
            value="v2",
        )

        decisions = evaluate_many(
            RequestEvaluationContext(
                anonymous_id="anon-a",
                request_overrides={"site_itmocraft_page_version": "v2"},
            ),
            ["site_itmocraft_page_version"],
        )

        self.assertEqual(decisions["site_itmocraft_page_version"], "legacy")

    def test_runtime_guard_uses_policy_not_compatibility_key_tuple(self):
        key = "policy_only_design_version"
        policy = replace(
            DESIGN_ROLLOUT_POLICY,
            allow_staff_preview=False,
        )
        spec = {
            "kind": "variant",
            "default_env": None,
            "default_fallback": "legacy",
            "variants": ("legacy", "v2"),
            "pages": ["policy-test"],
            "sticky": False,
            "description": "Policy-only regression flag.",
            "visual_impact": "Test only.",
            "rollout_policy": policy,
        }
        self.assertNotIn(key, DESIGN_FLAG_KEYS)

        with patch.dict(FEATURE_REGISTRY, {key: spec}):
            feature = FeatureDefinition.objects.create(
                key=key,
                kind=FeatureKind.VARIANT,
                default_value="legacy",
            )
            FeatureRule.objects.create(
                feature=feature,
                name="unsafe-everyone-v2",
                priority=10,
                rule_type=FeatureRuleType.EVERYONE,
                value="v2",
            )
            staff = User.objects.create_user(
                username="policy-preview-staff",
                email="policy-preview-staff@example.com",
                password="StrongPass123!",
                is_staff=True,
            )

            decisions = evaluate_many(
                RequestEvaluationContext(
                    user=staff,
                    anonymous_id="anon-policy",
                    page="policy-test",
                    request_overrides={key: "v2"},
                ),
                [key],
            )

        self.assertEqual(decisions[key], "legacy")

    def test_percentage_rollout_is_stable_for_same_identity(self):
        feature = self.boolean_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="half-rollout",
            priority=10,
            rule_type=FeatureRuleType.PERCENTAGE,
            value="true",
            percentage=50,
        )

        context = RequestEvaluationContext(
            anonymous_id="anon-fixed",
            page="itmocraft",
        )
        first = evaluate_many(context, ["profile_personalization_ui"])
        second = evaluate_many(context, ["profile_personalization_ui"])

        self.assertEqual(
            first["profile_personalization_ui"],
            second["profile_personalization_ui"],
        )

    def test_authenticated_user_identity_overrides_anonymous_default(
        self,
    ):
        user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="StrongPass123!",
        )
        feature = self.boolean_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="specific-user",
            priority=10,
            rule_type=FeatureRuleType.USER_ALLOWLIST,
            value="true",
            actor_ids=[str(user.pk)],
        )

        anonymous = evaluate_many(
            RequestEvaluationContext(anonymous_id="anon-before-login"),
            ["profile_personalization_ui"],
        )
        authenticated = evaluate_many(
            RequestEvaluationContext(
                user=user,
                anonymous_id="anon-before-login",
            ),
            ["profile_personalization_ui"],
        )

        self.assertFalse(anonymous["profile_personalization_ui"])
        self.assertTrue(authenticated["profile_personalization_ui"])

    def test_user_override_wins_over_matching_rule(self):
        user = User.objects.create_user(
            username="override-user",
            email="override@example.com",
            password="StrongPass123!",
        )
        feature = self.itmocraft_feature()
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
            ["site_itmocraft_page_version"],
        )

        self.assertEqual(decisions["site_itmocraft_page_version"], "legacy")

    # ─── Denylist Tests ──────────────────────────────────────────────

    def test_user_denylist_forces_default_value(self):
        """User in denylist gets the feature default, not the rule value."""
        user = User.objects.create_user(
            username="denied-user",
            email="denied@example.com",
            password="StrongPass123!",
        )
        feature = self.itmocraft_feature()
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
            ["site_itmocraft_page_version"],
        )
        self.assertEqual(decisions["site_itmocraft_page_version"], "legacy")

    def test_design_denylist_uses_safe_default_before_group_rule(self):
        user = User.objects.create_user(
            username="denied-design-tester",
            email="denied-design-tester@example.com",
            password="StrongPass123!",
        )
        group, _ = FeatureGroup.objects.get_or_create(
            slug=DESIGN_TESTER_GROUP_SLUG,
            defaults={"name": "Website design testers"},
        )
        group.members.clear()
        group.members.add(user)
        feature = self.itmocraft_feature()
        feature.default_value = "v2"
        feature.save(update_fields=["default_value"])
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
            name="design-testers-v2",
            priority=10,
            rule_type=FeatureRuleType.GROUP,
            value="v2",
            group_ids=[group.pk],
        )

        decisions = evaluate_many(
            RequestEvaluationContext(user=user, anonymous_id="anon"),
            ["site_itmocraft_page_version"],
        )

        self.assertEqual(decisions["site_itmocraft_page_version"], "legacy")

    def test_anonymous_denylist_forces_default_value(self):
        """Anonymous user in denylist gets the feature default."""
        feature = self.itmocraft_feature()
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
            ["site_itmocraft_page_version"],
        )
        self.assertEqual(decisions["site_itmocraft_page_version"], "legacy")

    # ─── Group Targeting Tests ───────────────────────────────────────

    def test_group_rule_matches_member(self):
        """User who is member of a target group gets the rule value."""
        user = User.objects.create_user(
            username="group-member",
            email="group-member@example.com",
            password="StrongPass123!",
        )
        group, _ = FeatureGroup.objects.get_or_create(
            slug=DESIGN_TESTER_GROUP_SLUG,
            defaults={"name": "Website design testers"},
        )
        group.members.clear()
        group.members.add(user)

        feature = self.itmocraft_feature()
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
            ["site_itmocraft_page_version"],
        )
        self.assertEqual(decisions["site_itmocraft_page_version"], "v2")

    def test_group_rule_does_not_match_non_member(self):
        """User not in the target group does not get the rule value."""
        user = User.objects.create_user(
            username="non-member",
            email="non-member@example.com",
            password="StrongPass123!",
        )
        group = FeatureGroup.objects.create(name="VIP Users", slug="vip-users")
        # user is NOT added to the group

        feature = self.itmocraft_feature()
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
            ["site_itmocraft_page_version"],
        )
        self.assertEqual(decisions["site_itmocraft_page_version"], "legacy")

    def test_design_v2_rejects_rule_for_a_different_group(self):
        user = User.objects.create_user(
            username="other-group-member",
            email="other-group-member@example.com",
            password="StrongPass123!",
        )
        group = FeatureGroup.objects.create(
            name="Other testers",
            slug="other-testers",
        )
        group.members.add(user)
        feature = self.itmocraft_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="other-group-v2",
            priority=10,
            rule_type=FeatureRuleType.GROUP,
            value="v2",
            group_ids=[group.pk],
        )

        decisions = evaluate_many(
            RequestEvaluationContext(user=user, anonymous_id="anon"),
            ["site_itmocraft_page_version"],
        )

        self.assertEqual(decisions["site_itmocraft_page_version"], "legacy")

    def test_design_v2_rejects_non_group_rule_for_design_tester(self):
        user = User.objects.create_user(
            username="design-member-everyone-rule",
            email="design-member-everyone-rule@example.com",
            password="StrongPass123!",
        )
        group, _ = FeatureGroup.objects.get_or_create(
            slug=DESIGN_TESTER_GROUP_SLUG,
            defaults={"name": "Website design testers"},
        )
        group.members.clear()
        group.members.add(user)
        feature = self.itmocraft_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="everyone-v2",
            priority=10,
            rule_type=FeatureRuleType.EVERYONE,
            value="v2",
        )

        decisions = evaluate_many(
            RequestEvaluationContext(user=user, anonymous_id="anon"),
            ["site_itmocraft_page_version"],
        )

        self.assertEqual(decisions["site_itmocraft_page_version"], "legacy")

    def test_design_v2_rejects_database_override_and_sticky_assignment(self):
        user = User.objects.create_user(
            username="design-member-stale-state",
            email="design-member-stale-state@example.com",
            password="StrongPass123!",
        )
        group, _ = FeatureGroup.objects.get_or_create(
            slug=DESIGN_TESTER_GROUP_SLUG,
            defaults={"name": "Website design testers"},
        )
        group.members.clear()
        group.members.add(user)
        feature = self.itmocraft_feature()
        feature.default_value = "v2"
        feature.sticky_assignment = True
        feature.save(update_fields=["default_value", "sticky_assignment"])
        FeatureOverride.objects.create(
            feature=feature,
            scope_type=FeatureOverrideScope.GLOBAL,
            value="v2",
        )
        ExperimentAssignment.objects.create(
            feature=feature,
            subject_type="user",
            subject_key=str(user.pk),
            page="itmocraft",
            value="v2",
        )

        decisions = evaluate_many(
            RequestEvaluationContext(
                user=user,
                anonymous_id="anon",
                page="itmocraft",
            ),
            ["site_itmocraft_page_version"],
        )

        self.assertEqual(decisions["site_itmocraft_page_version"], "legacy")

    def test_group_rule_does_not_match_anonymous(self):
        """Anonymous users never match group rules."""
        group = FeatureGroup.objects.create(
            name="Staff Group", slug="staff-group"
        )
        feature = self.boolean_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="group-on",
            priority=10,
            rule_type=FeatureRuleType.GROUP,
            value="true",
            group_ids=[group.pk],
        )

        decisions = evaluate_many(
            RequestEvaluationContext(anonymous_id="anon-visitor"),
            ["profile_personalization_ui"],
        )
        self.assertFalse(decisions["profile_personalization_ui"])

    def test_malformed_group_ids_fail_closed(self):
        user = User.objects.create_user(
            username="malformed-group-user",
            email="malformed-group-user@example.com",
            password="StrongPass123!",
        )
        feature = self.boolean_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="malformed-group",
            priority=10,
            rule_type=FeatureRuleType.GROUP,
            value="true",
            group_ids=["not-a-number"],
        )

        decisions = evaluate_many(
            RequestEvaluationContext(user=user, anonymous_id="anon"),
            ["profile_personalization_ui"],
        )

        self.assertFalse(decisions["profile_personalization_ui"])

    # ─── Disabled Rules / Inactive Features ──────────────────────────

    def test_disabled_rule_is_skipped(self):
        """A rule with enabled=False should not match."""
        feature = self.itmocraft_feature()
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
            ["site_itmocraft_page_version"],
        )
        self.assertEqual(decisions["site_itmocraft_page_version"], "legacy")

    def test_inactive_feature_returns_default(self):
        """A feature with active=False is not loaded."""
        feature = self.itmocraft_feature()
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
            ["site_itmocraft_page_version"],
        )
        # Falls through to DEFAULT_FEATURES since DB feature is inactive
        self.assertEqual(decisions["site_itmocraft_page_version"], "legacy")

    # ─── Page-Scoped Rules ───────────────────────────────────────────

    def test_page_scoped_rule_only_matches_matching_page(self):
        """A rule with page='itmocraft' only matches that page context."""
        feature = self.boolean_feature()
        FeatureRule.objects.create(
            feature=feature,
            name="itmocraft-only-on",
            priority=10,
            rule_type=FeatureRuleType.EVERYONE,
            value="true",
            page="itmocraft",
        )

        homepage_ctx = RequestEvaluationContext(
            anonymous_id="anon", page="itmocraft"
        )
        other_ctx = RequestEvaluationContext(
            anonymous_id="anon", page="account"
        )

        homepage_result = evaluate_many(
            homepage_ctx, ["profile_personalization_ui"]
        )
        other_result = evaluate_many(other_ctx, ["profile_personalization_ui"])

        self.assertTrue(homepage_result["profile_personalization_ui"])
        self.assertFalse(other_result["profile_personalization_ui"])

    # ─── Sticky Assignment Tests ─────────────────────────────────────

    def test_sticky_assignment_persists_and_reuses(self):
        """Once assigned, sticky assignment is returned on next eval."""
        feature = self.boolean_feature()
        feature.sticky_assignment = True
        feature.save(update_fields=["sticky_assignment"])
        FeatureRule.objects.create(
            feature=feature,
            name="everyone-on",
            priority=10,
            rule_type=FeatureRuleType.EVERYONE,
            value="true",
        )

        context = RequestEvaluationContext(anonymous_id="sticky-user", page="")
        first = evaluate_many(context, ["profile_personalization_ui"])
        self.assertTrue(first["profile_personalization_ui"])

        # Verify assignment was persisted
        assignment = ExperimentAssignment.objects.get(
            feature=feature, subject_key="sticky-user"
        )
        self.assertEqual(assignment.value, "True")

        # Now delete the rule — sticky value should still be returned
        feature.rules.all().delete()
        second = evaluate_many(context, ["profile_personalization_ui"])
        self.assertTrue(second["profile_personalization_ui"])

    # ─── Batch Evaluation Tests ──────────────────────────────────────

    def test_batch_evaluation_loads_multiple_features(self):
        """evaluate_many handles multiple keys in a single call."""
        FeatureDefinition.objects.create(
            key="profile_personalization_ui",
            kind=FeatureKind.BOOLEAN,
            default_value="true",
        )
        feature_b = FeatureDefinition.objects.create(
            key="profile_personalization_enforce",
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
            [
                "profile_personalization_ui",
                "profile_personalization_enforce",
                "missing_flag",
            ],
        )

        self.assertEqual(decisions["profile_personalization_ui"], True)
        self.assertEqual(decisions["profile_personalization_enforce"], True)
        self.assertEqual(decisions["missing_flag"], False)
