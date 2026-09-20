from __future__ import annotations

from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, RequestFactory, TestCase, override_settings

from backend.admin_site import SESSION_KEY_ADMIN_MFA_VERIFIED
from featureflags.admin import (
    FeatureDefinitionAdmin,
    FeatureGroupAdmin,
    rollout_index_view,
)
from featureflags.models import (
    FeatureDefinition,
    FeatureGroup,
    FeatureOverride,
    FeatureOverrideScope,
    FeatureRule,
    FeatureRuleType,
)
from featureflags.services import get_effective_default

User = get_user_model()


def grant(user, *permissions: str) -> None:
    for permission in permissions:
        app_label, codename = permission.split(".", 1)
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename,
            )
        )
    for cache_name in ("_perm_cache", "_user_perm_cache"):
        user.__dict__.pop(cache_name, None)


class RolloutIndexPrivacyTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.operator = User.objects.create_user(
            username="index-operator",
            password="StrongPass123!",
            is_staff=True,
        )
        grant(
            self.operator,
            "featureflags.view_featuredefinition",
            "featureflags.view_featurerule",
        )
        self.target = User.objects.create_user(
            username="private-target",
            email="private@example.com",
            password="StrongPass123!",
        )
        self.group = FeatureGroup.objects.create(
            name="Secret QA cohort",
            slug="secret-qa",
        )
        self.group.members.add(self.target)
        self.feature = FeatureDefinition.objects.create(
            key="profile_personalization_ui",
            kind="boolean",
            default_value="True",
        )

    def _index(self):
        request = self.factory.get("/admin/featureflags/rollouts/")
        request.user = self.operator
        return rollout_index_view(request, admin_site=admin.site)

    def test_targets_are_redacted_without_audience_permissions(self) -> None:
        FeatureRule.objects.create(
            feature=self.feature,
            name="Private users",
            rule_type=FeatureRuleType.USER_ALLOWLIST,
            value="false",
            page="account",
            actor_ids=[str(self.target.pk)],
        )
        FeatureRule.objects.create(
            feature=self.feature,
            name="Private group",
            rule_type=FeatureRuleType.GROUP,
            value="false",
            page="account",
            group_ids=[self.group.pk],
        )

        response = self._index()
        response.render()

        targets = {
            rollout["rule"].name: rollout["target"]
            for rollout in response.context_data["active_rollouts"]
        }
        self.assertIn(
            "нет права просмотра пользователей", targets["Private users"]
        )
        self.assertIn("нет права просмотра групп", targets["Private group"])
        self.assertNotContains(response, self.target.username)
        self.assertNotContains(response, self.group.name)

    def test_audience_permissions_reveal_only_their_own_target_type(
        self,
    ) -> None:
        FeatureRule.objects.create(
            feature=self.feature,
            name="Private users",
            rule_type=FeatureRuleType.USER_ALLOWLIST,
            value="false",
            page="account",
            actor_ids=[str(self.target.pk)],
        )
        FeatureRule.objects.create(
            feature=self.feature,
            name="Private group",
            rule_type=FeatureRuleType.GROUP,
            value="false",
            page="account",
            group_ids=[self.group.pk],
        )
        grant(self.operator, "featureflags.view_featuregroup")

        response = self._index()
        targets = {
            rollout["rule"].name: rollout["target"]
            for rollout in response.context_data["active_rollouts"]
        }

        self.assertEqual(
            targets["Private group"], "Secret QA cohort (secret-qa)"
        )
        self.assertIn(
            "нет права просмотра пользователей", targets["Private users"]
        )

    def test_index_explains_default_and_override_precedence(self) -> None:
        rule = FeatureRule.objects.create(
            feature=self.feature,
            name="Staff preview",
            rule_type=FeatureRuleType.STAFF,
            value="false",
            page="account",
        )
        FeatureOverride.objects.create(
            feature=self.feature,
            scope_type=FeatureOverrideScope.GLOBAL,
            value="false",
            note="Emergency support state",
        )

        response = self._index()
        rollout = next(
            item
            for item in response.context_data["active_rollouts"]
            if item["rule"].pk == rule.pk
        )

        self.assertEqual(rollout["default"], "Включено (true)")
        self.assertIn("Включено (true)", rollout["others"])
        self.assertTrue(
            any("override" in warning for warning in rollout["warnings"])
        )

    def test_inactive_definition_does_not_claim_rules_are_effective(
        self,
    ) -> None:
        self.feature.active = False
        self.feature.save(update_fields=("active", "updated_at"))
        rule = FeatureRule.objects.create(
            feature=self.feature,
            name="Stale enabled rule",
            rule_type=FeatureRuleType.STAFF,
            value="false",
            page="account",
        )
        model_admin = admin.site._registry[FeatureDefinition]

        self.assertIsInstance(model_admin, FeatureDefinitionAdmin)
        self.assertIn(
            "правила игнорируются",
            str(model_admin.effective_rollouts(self.feature)),
        )
        self.assertIn("архивировано", model_admin.rollout_state(self.feature))
        grant(
            self.operator,
            "featureflags.change_featurerule",
            "featureflags.view_featuredefinition",
        )
        rollout = next(
            item
            for item in self._index().context_data["active_rollouts"]
            if item["rule"].pk == rule.pk
        )
        self.assertFalse(rollout["can_stop"])

    @override_settings(FF_PROFILE_PERSONALIZATION_UI=False)
    def test_inactive_definition_uses_registry_environment_default(
        self,
    ) -> None:
        self.feature.active = False
        self.feature.save(update_fields=("active", "updated_at"))

        self.assertIs(get_effective_default(self.feature), False)

    def test_guarded_override_is_reported_as_policy_blocked(self) -> None:
        design = FeatureDefinition.objects.get(key="site_header_version")
        group = FeatureGroup.objects.get(slug="website-design-testers")
        FeatureRule.objects.create(
            feature=design,
            name="Header testers",
            rule_type=FeatureRuleType.GROUP,
            value="v2",
            group_ids=[group.pk],
        )
        FeatureOverride.objects.create(
            feature=design,
            scope_type=FeatureOverrideScope.GLOBAL,
            value="v2",
            note="Legacy impossible override",
        )
        grant(self.operator, "featureflags.view_featuregroup")

        rollout = next(
            item
            for item in self._index().context_data["active_rollouts"]
            if item["rule"].name == "Header testers"
        )

        self.assertTrue(
            any(
                "заблокированные политикой" in warning.lower()
                for warning in rollout["warnings"]
            )
        )
        self.assertFalse(
            any(
                "имеют приоритет" in warning.lower()
                for warning in rollout["warnings"]
            )
        )

    def test_draft_start_is_hidden_without_target_permission(self) -> None:
        draft = FeatureRule.objects.create(
            feature=self.feature,
            name="Private draft",
            rule_type=FeatureRuleType.USER_ALLOWLIST,
            value="false",
            page="account",
            actor_ids=[str(self.target.pk)],
            enabled=False,
        )
        grant(
            self.operator,
            "featureflags.change_featurerule",
            "featureflags.view_featuredefinition",
        )

        rollout = next(
            item
            for item in self._index().context_data["draft_rollouts"]
            if item["rule"].pk == draft.pk
        )
        self.assertFalse(rollout["can_start"])

        grant(self.operator, "auth.view_user")
        rollout = next(
            item
            for item in self._index().context_data["draft_rollouts"]
            if item["rule"].pk == draft.pk
        )
        self.assertTrue(rollout["can_start"])

    def test_advanced_draft_disallowed_by_guided_policy_has_no_start(
        self,
    ) -> None:
        draft = FeatureRule.objects.create(
            feature=self.feature,
            name="Advanced denylist",
            rule_type=FeatureRuleType.USER_DENYLIST,
            value="true",
            page="account",
            actor_ids=[str(self.target.pk)],
            enabled=False,
        )
        grant(
            self.operator,
            "featureflags.change_featurerule",
            "auth.view_user",
        )

        rollout = next(
            item
            for item in self._index().context_data["draft_rollouts"]
            if item["rule"].pk == draft.pk
        )

        self.assertFalse(rollout["can_start"])

    def test_archived_rule_is_hidden_from_non_superuser_index(self) -> None:
        archived = FeatureDefinition.objects.create(
            key="p129_a1_999__retired_admin_flag",
            kind="boolean",
            default_value="false",
            active=False,
        )
        FeatureRule.objects.create(
            feature=archived,
            name="Old target",
            rule_type=FeatureRuleType.USER_ALLOWLIST,
            value="true",
            actor_ids=[str(self.target.pk)],
        )

        response = self._index()

        self.assertNotIn(
            archived.pk,
            {
                item["rule"].feature_id
                for item in response.context_data["active_rollouts"]
            },
        )

    def test_archived_rule_is_omitted_from_superuser_console(self) -> None:
        archived = FeatureDefinition.objects.create(
            key="p129_a1_999__retired_superuser_flag",
            kind="boolean",
            default_value="false",
            active=False,
        )
        FeatureRule.objects.create(
            feature=archived,
            name="Unsupported archived rule",
            rule_type=FeatureRuleType.STAFF,
            value="true",
        )
        self.operator.is_superuser = True
        self.operator.save(update_fields=("is_superuser",))

        response = self._index()

        self.assertNotIn(
            archived.pk,
            {
                item["rule"].feature_id
                for item in response.context_data["active_rollouts"]
            },
        )
        self.assertNotIn(
            archived.pk,
            {
                item.feature_id
                for item in response.context_data["recent_history"]
            },
        )


class FeatureGroupRawAdminPermissionTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.operator = User.objects.create_user(
            username="group-operator",
            password="StrongPass123!",
            is_staff=True,
        )
        self.model_admin = admin.site._registry[FeatureGroup]

    def test_raw_group_admin_requires_full_operations_role(self) -> None:
        request = self.factory.get("/admin/featureflags/featuregroup/")
        request.user = self.operator
        grant(
            self.operator,
            "featureflags.view_featuregroup",
            "featureflags.change_featuregroup",
            "auth.view_user",
        )

        self.assertIsInstance(self.model_admin, FeatureGroupAdmin)
        self.assertFalse(self.model_admin.has_module_permission(request))
        self.assertFalse(self.model_admin.has_change_permission(request))

        grant(self.operator, "featureflags.delete_featuregroup")
        self.assertTrue(self.model_admin.has_module_permission(request))
        self.assertTrue(self.model_admin.has_change_permission(request))


@override_settings(
    DJANGO_ALLOWED_HOSTS=("admin.localhost", "api.localhost"),
    DJANGO_ADMIN_HOSTS=("admin.localhost",),
    DJANGO_API_HOSTS=("api.localhost",),
    WEBAUTHN_ADMIN_ORIGINS=("http://admin.localhost",),
)
class FeatureGroupRawAdminIntegrationTests(TestCase):
    def setUp(self) -> None:
        self.admin_mfa = patch(
            "backend.admin_site.admin_mfa_is_enabled",
            return_value=True,
        )
        self.middleware_mfa = patch(
            "backend.middleware.admin_mfa_is_enabled",
            return_value=True,
        )
        self.middleware_verified = patch(
            "backend.middleware.is_admin_mfa_verified",
            return_value=True,
        )
        for patcher in (
            self.admin_mfa,
            self.middleware_mfa,
            self.middleware_verified,
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

        self.operator = User.objects.create_user(
            username="safe-group-operator",
            password="StrongPass123!",
            is_staff=True,
        )
        grant(
            self.operator,
            "featureflags.view_featuregroup",
            "featureflags.change_featuregroup",
            "auth.view_user",
        )
        self.target = User.objects.create_user(
            username="crafted-target",
            password="StrongPass123!",
        )
        self.group = FeatureGroup.objects.create(
            name="Protected group",
            slug="protected-group",
        )
        self.client = Client()
        self.client.force_login(self.operator)
        session = self.client.session
        session[SESSION_KEY_ADMIN_MFA_VERIFIED] = True
        session.save()

    def test_crafted_membership_post_cannot_bypass_safe_action(self) -> None:
        response = self.client.post(
            f"/admin/featureflags/featuregroup/{self.group.pk}/change/",
            {
                "name": self.group.name,
                "slug": self.group.slug,
                "description": "crafted update",
                "members": [self.target.pk],
                "_save": "Save",
            },
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.group.members.filter(pk=self.target.pk).exists())

    def test_crafted_stop_cannot_mutate_archived_rule(self) -> None:
        grant(
            self.operator,
            "featureflags.change_featurerule",
            "featureflags.view_featuredefinition",
        )
        archived = FeatureDefinition.objects.create(
            key="p129_a1_999__retired_stop_flag",
            kind="boolean",
            default_value="false",
            active=False,
        )
        rule = FeatureRule.objects.create(
            feature=archived,
            name="Archived rollout",
            rule_type=FeatureRuleType.STAFF,
            value="true",
        )

        response = self.client.post(
            f"/admin/featureflags/rollouts/{rule.pk}/stop/",
            {"reason": "Crafted archived stop"},
            HTTP_HOST="admin.localhost",
            HTTP_ORIGIN="http://admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        rule.refresh_from_db()
        self.assertTrue(rule.enabled)

    def test_crafted_start_cannot_restart_hidden_stopped_rollout(self) -> None:
        grant(
            self.operator,
            "featureflags.change_featurerule",
            "featureflags.view_featuredefinition",
        )
        feature = FeatureDefinition.objects.create(
            key="profile_personalization_interstitial",
            kind="boolean",
            default_value="true",
        )
        rule = FeatureRule.objects.create(
            feature=feature,
            name="Originally active rollout",
            rule_type=FeatureRuleType.STAFF,
            value="false",
            page="account",
        )
        rule.enabled = False
        rule.save(update_fields=("enabled", "updated_at"))

        response = self.client.post(
            f"/admin/featureflags/rollouts/{rule.pk}/start/",
            {"reason": "Crafted hidden restart"},
            HTTP_HOST="admin.localhost",
            HTTP_ORIGIN="http://admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        rule.refresh_from_db()
        self.assertFalse(rule.enabled)

    def test_raw_rule_and_override_urls_hide_archived_records(self) -> None:
        grant(
            self.operator,
            "featureflags.view_featurerule",
            "featureflags.change_featurerule",
            "featureflags.delete_featurerule",
            "featureflags.view_featureoverride",
            "featureflags.change_featureoverride",
        )
        archived = FeatureDefinition.objects.create(
            key="p129_a1_999__retired_raw_records",
            kind="boolean",
            default_value="false",
            active=False,
        )
        rule = FeatureRule.objects.create(
            feature=archived,
            name="Archived raw rule",
            rule_type=FeatureRuleType.STAFF,
            value="true",
        )
        override = FeatureOverride.objects.create(
            feature=archived,
            scope_type=FeatureOverrideScope.GLOBAL,
            value="false",
            note="Archived raw override",
        )

        rule_response = self.client.get(
            f"/admin/featureflags/featurerule/{rule.pk}/change/",
            HTTP_HOST="admin.localhost",
        )
        override_response = self.client.get(
            f"/admin/featureflags/featureoverride/{override.pk}/change/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(rule_response.status_code, 302)
        self.assertEqual(override_response.status_code, 302)
