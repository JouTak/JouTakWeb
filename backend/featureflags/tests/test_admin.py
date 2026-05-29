from __future__ import annotations

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase

from featureflags.admin import (
    FeatureOverrideAdminForm,
    FeatureRuleAdminForm,
)
from featureflags.models import (
    FeatureDefinition,
    FeatureGroup,
    FeatureKind,
    FeatureOverride,
    FeatureOverrideScope,
    FeatureRule,
    FeatureRuleType,
)

User = get_user_model()


class FeatureFlagsAdminTests(TestCase):
    def setUp(self) -> None:
        self.feature = FeatureDefinition.objects.create(
            key="admin_feature",
            kind=FeatureKind.BOOLEAN,
            default_value="false",
        )
        self.user_one = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="StrongPass123!",
        )
        self.user_two = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="StrongPass123!",
        )
        self.group = FeatureGroup.objects.create(
            name="Dev Testers",
            slug="dev-testers",
        )
        self.group.members.add(self.user_one)

    def test_feature_rule_form_serializes_user_targets(self) -> None:
        form = FeatureRuleAdminForm(
            data={
                "feature": self.feature.pk,
                "name": "User rollout",
                "priority": 10,
                "rule_type": FeatureRuleType.USER_ALLOWLIST,
                "value": "true",
                "page": "",
                "percentage": "",
                "enabled": "on",
                "target_users": [str(self.user_one.pk), str(self.user_two.pk)],
                "anonymous_ids": "",
                "target_groups": [],
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        rule = form.save()

        self.assertEqual(
            rule.actor_ids, [str(self.user_one.pk), str(self.user_two.pk)]
        )
        self.assertEqual(rule.group_ids, [])

    def test_feature_rule_form_serializes_group_targets(self) -> None:
        form = FeatureRuleAdminForm(
            data={
                "feature": self.feature.pk,
                "name": "Group rollout",
                "priority": 20,
                "rule_type": FeatureRuleType.GROUP,
                "value": "true",
                "page": "",
                "percentage": "",
                "enabled": "on",
                "target_users": [],
                "anonymous_ids": "",
                "target_groups": [str(self.group.pk)],
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        rule = form.save()

        self.assertEqual(rule.group_ids, [self.group.pk])
        self.assertEqual(rule.actor_ids, [])

    def test_feature_rule_form_uses_human_readable_user_labels(self) -> None:
        form = FeatureRuleAdminForm()

        self.assertEqual(
            form.fields["target_users"].label_from_instance(self.user_one),
            "alice <alice@example.com>",
        )

    def test_feature_override_form_serializes_user_scope(self) -> None:
        form = FeatureOverrideAdminForm(
            data={
                "feature": self.feature.pk,
                "scope_type": FeatureOverrideScope.USER,
                "target_user": self.user_one.pk,
                "anonymous_scope": "",
                "value": "true",
                "enabled": "on",
                "note": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        override = form.save()

        self.assertEqual(override.scope_value, str(self.user_one.pk))

    def test_feature_override_form_uses_human_readable_user_labels(
        self,
    ) -> None:
        form = FeatureOverrideAdminForm()

        self.assertEqual(
            form.fields["target_user"].label_from_instance(self.user_two),
            "bob <bob@example.com>",
        )

    def test_feature_override_form_serializes_anonymous_scope(self) -> None:
        form = FeatureOverrideAdminForm(
            data={
                "feature": self.feature.pk,
                "scope_type": FeatureOverrideScope.ANONYMOUS,
                "target_user": "",
                "anonymous_scope": "anon-123",
                "value": "true",
                "enabled": "on",
                "note": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        override = form.save()

        self.assertEqual(override.scope_value, "anon-123")

    def test_feature_rule_admin_displays_human_readable_targets(self) -> None:
        rule = FeatureRule.objects.create(
            feature=self.feature,
            name="Group rollout",
            priority=10,
            rule_type=FeatureRuleType.GROUP,
            value="true",
            group_ids=[self.group.pk],
        )

        admin_instance = admin.site._registry[FeatureRule]

        self.assertIn("Dev Testers", admin_instance.target_summary(rule))
        self.assertNotIn(
            str(self.group.pk), admin_instance.target_summary(rule)
        )

    def test_feature_override_admin_displays_human_readable_scope(
        self,
    ) -> None:
        override = FeatureOverride.objects.create(
            feature=self.feature,
            scope_type=FeatureOverrideScope.USER,
            scope_value=str(self.user_two.pk),
            value="true",
        )

        admin_instance = admin.site._registry[FeatureOverride]

        self.assertIn("bob", admin_instance.scope_summary(override))
        self.assertNotIn(
            str(self.user_two.pk), admin_instance.scope_summary(override)
        )
