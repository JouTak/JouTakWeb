from __future__ import annotations

import json
from unittest.mock import patch

from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, RequestFactory, TestCase, override_settings

from backend.admin_site import SESSION_KEY_ADMIN_MFA_VERIFIED
from featureflags.admin import (
    ExperimentAssignmentAdmin,
    FeatureOverrideAdmin,
    rollout_add_view,
    rollout_index_view,
    rollout_stop_view,
)
from featureflags.admin_services import (
    add_design_tester,
    create_rollout,
    start_rollout,
    stop_rollout,
)
from featureflags.forms import (
    FeatureOverrideAdminForm,
    FeatureRuleAdminForm,
    GuidedRolloutForm,
    RolloutAudience,
    value_choices,
)
from featureflags.models import (
    ExperimentAssignment,
    FeatureDefinition,
    FeatureGroup,
    FeatureOverride,
    FeatureOverrideScope,
    FeatureRule,
    FeatureRuleType,
)
from featureflags.registry import DESIGN_TESTER_GROUP_SLUG

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


class RegistryAwareAdminFormTests(TestCase):
    def setUp(self) -> None:
        self.feature = FeatureDefinition.objects.create(
            key="profile_personalization_ui",
            kind="boolean",
            default_value="true",
        )
        self.operator = User.objects.create_user(
            username="rollout-operator",
            email="operator@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.target = User.objects.create_user(
            username="rollout-target",
            email="target@example.com",
            password="StrongPass123!",
        )
        self.group = FeatureGroup.objects.create(
            name="QA",
            slug="qa",
        )

    def guided_data(self, **overrides) -> dict:
        data = {
            "feature": self.feature.pk,
            "value": "false",
            "page": "account",
            "audience": RolloutAudience.STAFF,
            "target_groups": [],
            "target_users": [],
            "percentage": "",
            "name": "Profile UI staff preview",
            "reason": "Verify the new account layout",
            "enabled": "on",
            "confirm_rollout": "on",
        }
        data.update(overrides)
        return data

    def test_boolean_choices_are_canonical_and_human_readable(self) -> None:
        self.assertEqual(
            value_choices(self.feature.key),
            (("true", "Включено (true)"), ("false", "Выключено (false)")),
        )

    def test_rule_form_clears_irrelevant_targets(self) -> None:
        form = FeatureRuleAdminForm(
            data={
                "feature": self.feature.pk,
                "name": "Staff only",
                "priority": 100,
                "rule_type": FeatureRuleType.STAFF,
                "value": "false",
                "page": "account",
                "percentage": 75,
                "enabled": "on",
                "audit_reason": "Create staff rule",
                "target_users": [self.target.pk],
                "target_groups": [self.group.pk],
                "anonymous_ids": "anon-id",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        rule = form.save()
        self.assertEqual(rule.actor_ids, [])
        self.assertEqual(rule.group_ids, [])
        self.assertIsNone(rule.percentage)

    def test_denylist_uses_registry_default_instead_of_posted_value(
        self,
    ) -> None:
        form = FeatureRuleAdminForm(
            data={
                "feature": self.feature.pk,
                "name": "Exclude one user",
                "priority": 100,
                "rule_type": FeatureRuleType.USER_DENYLIST,
                "value": "false",
                "page": "account",
                "percentage": "",
                "enabled": "on",
                "audit_reason": "Create denylist rule",
                "target_users": [self.target.pk],
                "target_groups": [],
                "anonymous_ids": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().value, "true")

    def test_global_override_requires_explicit_confirmation(self) -> None:
        form = FeatureOverrideAdminForm(
            data={
                "feature": self.feature.pk,
                "scope_type": FeatureOverrideScope.GLOBAL,
                "value": "false",
                "enabled": "on",
                "note": "Emergency rollback",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("confirm_global", form.errors)

    def test_guarded_variant_cannot_be_saved_as_noop_override(self) -> None:
        design = FeatureDefinition.objects.get(key="site_header_version")
        form = FeatureOverrideAdminForm(
            data={
                "feature": design.pk,
                "scope_type": FeatureOverrideScope.GLOBAL,
                "value": "v2",
                "enabled": "on",
                "note": "Unsafe design bypass",
                "confirm_global": "on",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("value", form.errors)

    def test_duplicate_override_is_a_form_error(self) -> None:
        FeatureOverride.objects.create(
            feature=self.feature,
            scope_type=FeatureOverrideScope.USER,
            scope_value=str(self.target.pk),
            value="false",
            note="Existing support override",
        )
        form = FeatureOverrideAdminForm(
            data={
                "feature": self.feature.pk,
                "scope_type": FeatureOverrideScope.USER,
                "target_user": self.target.pk,
                "value": "true",
                "enabled": "on",
                "note": "Another support override",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("уже существует", str(form.errors).lower())

    def test_guided_form_rejects_crafted_user_audience_without_permission(
        self,
    ) -> None:
        form = GuidedRolloutForm(
            data=self.guided_data(
                audience=RolloutAudience.USERS,
                target_users=[self.target.pk],
            ),
            request_user=self.operator,
            require_confirmation=True,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("audience", form.errors)

    def test_disabled_draft_can_coexist_with_active_rollout(self) -> None:
        FeatureRule.objects.create(
            feature=self.feature,
            name="Current rollout",
            priority=10,
            rule_type=FeatureRuleType.STAFF,
            value="false",
            page="account",
            enabled=True,
        )
        data = self.guided_data()
        data.pop("enabled")
        form = GuidedRolloutForm(
            data=data,
            request_user=self.operator,
            require_confirmation=True,
        )

        self.assertTrue(form.is_valid(), form.errors)
        draft = create_rollout(
            cleaned_data=form.cleaned_data,
            user=self.operator,
        )
        self.assertFalse(draft.enabled)

    def test_equivalent_draft_creation_is_idempotent(self) -> None:
        data = self.guided_data()
        data.pop("enabled")
        form = GuidedRolloutForm(
            data=data,
            request_user=self.operator,
            require_confirmation=True,
        )
        self.assertTrue(form.is_valid(), form.errors)

        first = create_rollout(
            cleaned_data=form.cleaned_data,
            user=self.operator,
        )
        second = create_rollout(
            cleaned_data=form.cleaned_data,
            user=self.operator,
        )

        self.assertEqual(first.pk, second.pk)
        self.assertTrue(first._rollout_was_created)
        self.assertFalse(second._rollout_was_created)
        self.assertEqual(
            FeatureRule.objects.filter(feature=self.feature).count(), 1
        )

    def test_stopped_rollout_is_not_reused_or_restartable_as_draft(
        self,
    ) -> None:
        data = self.guided_data()
        data.pop("enabled")
        form = GuidedRolloutForm(
            data=data,
            request_user=self.operator,
            require_confirmation=True,
        )
        self.assertTrue(form.is_valid(), form.errors)
        original = create_rollout(
            cleaned_data=form.cleaned_data,
            user=self.operator,
        )
        start_rollout(
            rule_id=original.pk,
            user=self.operator,
            reason="QA approved the first rollout",
        )
        stop_rollout(
            rule_id=original.pk,
            user=self.operator,
            reason="First rollout completed",
        )

        replacement = create_rollout(
            cleaned_data=form.cleaned_data,
            user=self.operator,
        )

        self.assertNotEqual(replacement.pk, original.pk)
        self.assertTrue(replacement._rollout_was_created)
        with self.assertRaisesMessage(
            ValidationError,
            "только раскат, созданный как черновик",
        ):
            start_rollout(
                rule_id=original.pk,
                user=self.operator,
                reason="Do not restart completed rollout",
            )

    def test_create_and_stop_keep_actor_reason_history(self) -> None:
        form = GuidedRolloutForm(
            data=self.guided_data(),
            request_user=self.operator,
            require_confirmation=True,
        )
        self.assertTrue(form.is_valid(), form.errors)

        rule = create_rollout(
            cleaned_data=form.cleaned_data,
            user=self.operator,
        )
        created = rule.history.first()
        self.assertEqual(created.history_user, self.operator)
        self.assertEqual(
            created.history_change_reason,
            "Verify the new account layout",
        )

        stop_rollout(
            rule_id=rule.pk,
            user=self.operator,
            reason="Experiment has enough feedback",
        )
        stopped = rule.history.first()
        self.assertEqual(stopped.history_user, self.operator)
        self.assertEqual(
            stopped.history_change_reason,
            "Experiment has enough feedback",
        )

    def test_draft_can_be_started_with_audited_reason(self) -> None:
        data = self.guided_data()
        data.pop("enabled")
        form = GuidedRolloutForm(
            data=data,
            request_user=self.operator,
            require_confirmation=True,
        )
        self.assertTrue(form.is_valid(), form.errors)
        draft = create_rollout(
            cleaned_data=form.cleaned_data,
            user=self.operator,
        )

        started = start_rollout(
            rule_id=draft.pk,
            user=self.operator,
            reason="QA approved this rollout",
        )

        self.assertTrue(started.enabled)
        self.assertEqual(
            started.history.first().history_change_reason,
            "QA approved this rollout",
        )

    def test_user_draft_start_requires_user_lookup_permission(self) -> None:
        draft = FeatureRule.objects.create(
            feature=self.feature,
            name="Selected users",
            rule_type=FeatureRuleType.USER_ALLOWLIST,
            value="false",
            page="account",
            actor_ids=[str(self.target.pk)],
            enabled=False,
        )

        with self.assertRaisesMessage(
            ValidationError, "просматривать пользователей"
        ):
            start_rollout(
                rule_id=draft.pk,
                user=self.operator,
                reason="Approved by QA team",
            )

        draft.refresh_from_db()
        self.assertFalse(draft.enabled)

    def test_group_draft_start_requires_group_lookup_permission(self) -> None:
        draft = FeatureRule.objects.create(
            feature=self.feature,
            name="Selected group",
            rule_type=FeatureRuleType.GROUP,
            value="false",
            page="account",
            group_ids=[self.group.pk],
            enabled=False,
        )

        with self.assertRaisesMessage(ValidationError, "просматривать группы"):
            start_rollout(
                rule_id=draft.pk,
                user=self.operator,
                reason="Approved by QA team",
            )

        draft.refresh_from_db()
        self.assertFalse(draft.enabled)

    def test_start_rejects_malformed_required_group_ids(self) -> None:
        grant(self.operator, "featureflags.view_featuregroup")
        design = FeatureDefinition.objects.get(key="site_header_version")
        draft = FeatureRule.objects.create(
            feature=design,
            name="Corrupt design group",
            rule_type=FeatureRuleType.GROUP,
            value="v2",
            page="",
            group_ids=["not-a-group-id"],
            enabled=False,
        )

        with self.assertRaisesMessage(ValidationError, "повреждён"):
            start_rollout(
                rule_id=draft.pk,
                user=self.operator,
                reason="Approved by QA team",
            )

        draft.refresh_from_db()
        self.assertFalse(draft.enabled)

    def test_start_rejects_invalid_percentage_draft(self) -> None:
        grant(self.operator, "featureflags.change_featuredefinition")
        draft = FeatureRule.objects.create(
            feature=self.feature,
            name="Invalid percentage",
            rule_type=FeatureRuleType.PERCENTAGE,
            value="false",
            page="account",
            percentage=101,
            enabled=False,
        )

        with self.assertRaisesMessage(ValidationError, "процент от 0 до 100"):
            start_rollout(
                rule_id=draft.pk,
                user=self.operator,
                reason="Approved by QA team",
            )

        draft.refresh_from_db()
        self.assertFalse(draft.enabled)

    def test_guided_initial_uses_runtime_effective_default(self) -> None:
        self.feature.default_value = "TRUE"
        self.feature.save(update_fields=("default_value", "updated_at"))

        form = GuidedRolloutForm(
            initial={"feature": self.feature},
            request_user=self.operator,
        )

        self.assertEqual(form.initial["value"], "false")
        self.assertTrue(form.page_is_fixed)
        self.assertIn(
            "Персонализация профиля",
            form.fields["feature"].label_from_instance(self.feature),
        )

    def test_advanced_design_metadata_only_offers_group_rule(self) -> None:
        form = FeatureRuleAdminForm()
        metadata = json.loads(
            form.fields["feature"].widget.attrs["data-registry-options"]
        )
        design = FeatureDefinition.objects.get(key="site_header_version")

        self.assertEqual(
            metadata[str(design.pk)]["rule_types"],
            [[FeatureRuleType.GROUP, "Группа"]],
        )
        self.assertEqual(metadata[str(design.pk)]["suggested_value"], "v2")
        self.assertEqual(
            metadata[str(self.feature.pk)]["suggested_value"],
            "false",
        )

    def test_service_revalidates_design_policy(self) -> None:
        design = FeatureDefinition.objects.get(key="site_header_version")

        with self.assertRaises(ValidationError):
            create_rollout(
                cleaned_data={
                    "feature": design,
                    "value": "v2",
                    "page": "",
                    "audience": RolloutAudience.EVERYONE,
                    "target_groups": [],
                    "target_users": [],
                    "percentage": None,
                    "name": "Unsafe",
                    "reason": "Unsafe broad rollout",
                    "enabled": False,
                },
                user=self.operator,
            )

    def test_design_tester_quick_action_is_audited(self) -> None:
        design_group = FeatureGroup.objects.get(slug=DESIGN_TESTER_GROUP_SLUG)
        grant(
            self.operator,
            "featureflags.change_featuregroup",
            "auth.view_user",
        )

        add_design_tester(
            target_user=self.target,
            user=self.operator,
            reason="Frontend acceptance testing",
        )

        self.assertTrue(
            design_group.members.filter(pk=self.target.pk).exists()
        )
        log = LogEntry.objects.get(user=self.operator)
        self.assertIn("Frontend acceptance testing", log.change_message)


class RolloutAdminPermissionTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.staff = User.objects.create_user(
            username="limited-staff",
            password="StrongPass123!",
            is_staff=True,
        )

    def test_low_level_override_page_requires_full_operator_permissions(
        self,
    ) -> None:
        request = self.factory.get("/admin/featureflags/featureoverride/")
        request.user = self.staff
        model_admin = admin.site._registry[FeatureOverride]
        self.assertIsInstance(model_admin, FeatureOverrideAdmin)
        self.assertFalse(model_admin.has_module_permission(request))

        grant(
            self.staff,
            "featureflags.view_featureoverride",
            "featureflags.change_featureoverride",
            "auth.view_user",
        )
        self.assertTrue(model_admin.has_module_permission(request))

    def test_assignment_direct_view_is_system_only(self) -> None:
        request = self.factory.get("/admin/featureflags/experimentassignment/")
        request.user = self.staff
        grant(self.staff, "featureflags.view_experimentassignment")
        model_admin = admin.site._registry[ExperimentAssignment]
        self.assertIsInstance(model_admin, ExperimentAssignmentAdmin)
        self.assertFalse(model_admin.has_view_permission(request))

    def test_rollout_index_requires_rule_history_permission(self) -> None:
        request = self.factory.get("/admin/featureflags/rollouts/")
        request.user = self.staff
        grant(self.staff, "featureflags.view_featuredefinition")

        with self.assertRaises(PermissionDenied):
            rollout_index_view(request, admin_site=admin.site)

    def test_review_post_does_not_create_rule(self) -> None:
        feature = FeatureDefinition.objects.create(
            key="profile_personalization_interstitial",
            kind="boolean",
            default_value="true",
        )
        grant(
            self.staff,
            "featureflags.add_featurerule",
            "featureflags.view_featuredefinition",
            "featureflags.view_featuregroup",
            "featureflags.view_featurerule",
        )
        request = self.factory.post(
            "/admin/featureflags/rollouts/new/",
            {
                "feature": feature.pk,
                "value": "false",
                "page": "account",
                "audience": RolloutAudience.STAFF,
                "reason": "Review this staff preview",
                "enabled": "on",
                "_review": "1",
            },
        )
        request.user = self.staff
        request._dont_enforce_csrf_checks = True

        response = rollout_add_view(request, admin_site=admin.site)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            FeatureRule.objects.filter(feature=feature).count(), 0
        )
        self.assertTrue(response.context_data["review"])

    def test_get_stop_is_method_safe_and_does_not_mutate(self) -> None:
        feature = FeatureDefinition.objects.create(
            key="profile_personalization_enforce",
            kind="boolean",
            default_value="false",
        )
        rule = FeatureRule.objects.create(
            feature=feature,
            name="Current",
            rule_type=FeatureRuleType.STAFF,
            value="true",
            page="",
        )
        grant(
            self.staff,
            "featureflags.change_featurerule",
            "featureflags.view_featuredefinition",
        )
        request = self.factory.get(
            f"/admin/featureflags/rollouts/{rule.pk}/stop/"
        )
        request.user = self.staff

        response = rollout_stop_view(
            request,
            rule.pk,
            admin_site=admin.site,
        )

        self.assertEqual(response.status_code, 405)
        rule.refresh_from_db()
        self.assertTrue(rule.enabled)


@override_settings(
    DJANGO_ALLOWED_HOSTS=(
        "localhost",
        "127.0.0.1",
        "admin.localhost",
        "api.localhost",
    ),
    DJANGO_ADMIN_HOSTS=("admin.localhost",),
    DJANGO_API_HOSTS=("api.localhost",),
)
class RolloutAdminIntegrationTests(TestCase):
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
            username="admin-flow-operator",
            email="flow@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        grant(
            self.operator,
            "featureflags.add_featurerule",
            "featureflags.view_featuredefinition",
            "featureflags.view_featuregroup",
            "featureflags.view_featurerule",
        )
        self.feature = FeatureDefinition.objects.create(
            key="profile_personalization_ui",
            kind="boolean",
            default_value="true",
        )
        self.client.force_login(self.operator)
        session = self.client.session
        session[SESSION_KEY_ADMIN_MFA_VERIFIED] = True
        session.save()

    def rollout_data(self, action: str, *, confirm: bool = False) -> dict:
        data = {
            "feature": self.feature.pk,
            "value": "false",
            "page": "account",
            "audience": RolloutAudience.STAFF,
            "reason": "Review from integration test",
            "enabled": "on",
            action: "1",
        }
        if confirm:
            data["confirm_rollout"] = "on"
        return data

    def test_real_route_requires_mfa_verified_session(self) -> None:
        session = self.client.session
        session.pop(SESSION_KEY_ADMIN_MFA_VERIFIED, None)
        session.save()

        response = self.client.get(
            "/admin/featureflags/rollouts/new/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_review_then_confirmation_creates_exactly_once(self) -> None:
        review = self.client.post(
            "/admin/featureflags/rollouts/new/",
            self.rollout_data("_review"),
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(review.status_code, 200)
        self.assertContains(review, "Проверьте итог перед сохранением")
        self.assertFalse(
            FeatureRule.objects.filter(feature=self.feature).exists()
        )

        create_data = self.rollout_data("_create", confirm=True)
        create_data["review_token"] = review.context_data["review_token"]
        created = self.client.post(
            "/admin/featureflags/rollouts/new/",
            create_data,
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(created.status_code, 302)
        rules = FeatureRule.objects.filter(feature=self.feature)
        self.assertEqual(rules.count(), 1)
        self.assertEqual(
            rules.get().history.first().history_user, self.operator
        )

    def test_signed_draft_confirmation_replay_creates_one_draft(self) -> None:
        review_data = self.rollout_data("_review")
        review_data.pop("enabled")
        review = self.client.post(
            "/admin/featureflags/rollouts/new/",
            review_data,
            HTTP_HOST="admin.localhost",
        )
        self.assertEqual(review.status_code, 200)

        create_data = self.rollout_data("_create", confirm=True)
        create_data.pop("enabled")
        create_data["review_token"] = review.context_data["review_token"]
        first = self.client.post(
            "/admin/featureflags/rollouts/new/",
            create_data,
            HTTP_HOST="admin.localhost",
        )
        second = self.client.post(
            "/admin/featureflags/rollouts/new/",
            create_data,
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        rule = FeatureRule.objects.get(feature=self.feature)
        self.assertFalse(rule.enabled)
        self.assertEqual(
            LogEntry.objects.filter(object_id=str(rule.pk)).count(), 1
        )

    def test_stopped_rollout_is_not_listed_as_draft(self) -> None:
        review_data = self.rollout_data("_review", confirm=True)
        review_data.pop("enabled")
        form = GuidedRolloutForm(
            data=review_data,
            request_user=self.operator,
            require_confirmation=True,
        )
        self.assertTrue(form.is_valid(), form.errors)
        rule = create_rollout(
            cleaned_data=form.cleaned_data,
            user=self.operator,
        )
        start_rollout(
            rule_id=rule.pk,
            user=self.operator,
            reason="QA approved this rollout",
        )
        stop_rollout(
            rule_id=rule.pk,
            user=self.operator,
            reason="Rollout completed",
        )

        response = self.client.get(
            "/admin/featureflags/rollouts/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 200)
        draft_ids = {
            rollout["rule"].pk
            for rollout in response.context["draft_rollouts"]
        }
        self.assertNotIn(rule.pk, draft_ids)

    def test_group_review_preserves_target_and_shows_member_count(
        self,
    ) -> None:
        target = User.objects.create_user(
            username="group-review-target",
            password="StrongPass123!",
        )
        group = FeatureGroup.objects.create(
            name="Product QA",
            slug="product-qa",
        )
        group.members.add(target)
        review_data = {
            **self.rollout_data("_review"),
            "audience": RolloutAudience.GROUP,
            "target_groups": [group.pk],
        }

        review = self.client.post(
            "/admin/featureflags/rollouts/new/",
            review_data,
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(review.status_code, 200)
        self.assertContains(review, "Product QA (product-qa), участников: 1")
        self.assertContains(review, "Показывает интерфейс персонализации")
        self.assertContains(review, "Показывает или скрывает подсказки")
        self.assertContains(
            review,
            f'<option value="{group.pk}" selected>Product QA</option>',
            html=True,
        )

        create_data = {
            **review_data,
            "_create": "1",
            "confirm_rollout": "on",
            "review_token": review.context_data["review_token"],
        }
        create_data.pop("_review")
        created = self.client.post(
            "/admin/featureflags/rollouts/new/",
            create_data,
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(created.status_code, 302)
        self.assertEqual(
            FeatureRule.objects.get(feature=self.feature).group_ids,
            [group.pk],
        )

    def test_direct_create_without_review_token_does_not_mutate(self) -> None:
        response = self.client.post(
            "/admin/featureflags/rollouts/new/",
            self.rollout_data("_create", confirm=True),
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Проверьте итог ещё раз")
        self.assertFalse(
            FeatureRule.objects.filter(feature=self.feature).exists()
        )

    def test_invalid_review_renders_errors_without_signing_or_mutation(
        self,
    ) -> None:
        data = self.rollout_data("_review")
        data.pop("reason")

        response = self.client.post(
            "/admin/featureflags/rollouts/new/",
            data,
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("reason", response.context_data["form"].errors)
        self.assertFalse(response.context_data["review"])
        self.assertEqual(response.context_data["review_token"], "")
        self.assertNotContains(response, 'name="_create"')
        self.assertFalse(
            FeatureRule.objects.filter(feature=self.feature).exists()
        )

    def test_mutating_route_rejects_missing_csrf_token(self) -> None:
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.operator)
        session = csrf_client.session
        session[SESSION_KEY_ADMIN_MFA_VERIFIED] = True
        session.save()

        response = csrf_client.post(
            "/admin/featureflags/rollouts/new/",
            self.rollout_data("_create", confirm=True),
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            FeatureRule.objects.filter(feature=self.feature).exists()
        )

    def test_index_does_not_leak_history_without_rule_view_permission(
        self,
    ) -> None:
        permission = Permission.objects.get(
            content_type__app_label="featureflags",
            codename="view_featurerule",
        )
        self.operator.user_permissions.remove(permission)
        for cache_name in ("_perm_cache", "_user_perm_cache"):
            self.operator.__dict__.pop(cache_name, None)

        response = self.client.get(
            "/admin/featureflags/rollouts/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 403)

    def test_design_tester_lookup_requires_user_view_permission(self) -> None:
        grant(self.operator, "featureflags.change_featuregroup")

        denied = self.client.get(
            "/admin/featureflags/design-testers/add/",
            HTTP_HOST="admin.localhost",
        )
        self.assertEqual(denied.status_code, 403)

        grant(self.operator, "auth.view_user")
        allowed = self.client.get(
            "/admin/featureflags/design-testers/add/",
            HTTP_HOST="admin.localhost",
        )
        self.assertEqual(allowed.status_code, 200)

    def test_stop_get_is_405_and_does_not_change_rule(self) -> None:
        grant(self.operator, "featureflags.change_featurerule")
        rule = FeatureRule.objects.create(
            feature=self.feature,
            name="Running",
            rule_type=FeatureRuleType.STAFF,
            value="false",
            page="account",
        )

        response = self.client.get(
            f"/admin/featureflags/rollouts/{rule.pk}/stop/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 405)
        rule.refresh_from_db()
        self.assertTrue(rule.enabled)

    def test_form_uses_vertical_layout_without_tabular_inlines(self) -> None:
        response = self.client.get(
            f"/admin/featureflags/featuredefinition/{self.feature.pk}/change/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "tabular inline-related")
        self.assertContains(response, "Что увидит пользователь")

    def test_guided_single_registry_page_is_hidden_and_submitted(self) -> None:
        response = self.client.get(
            f"/admin/featureflags/rollouts/new/?feature={self.feature.pk}",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'data-field="page" hidden',
        )
        self.assertContains(
            response,
            '<option value="account" selected>account</option>',
            html=True,
        )

    def test_archived_definition_direct_url_is_hidden_from_operator(
        self,
    ) -> None:
        archived = FeatureDefinition.objects.create(
            key="p129_a1_999__retired_flag",
            kind="boolean",
            default_value="false",
            active=False,
        )

        response = self.client.get(
            f"/admin/featureflags/featuredefinition/{archived.pk}/change/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            response["Location"],
            ("/admin/", "/admin/featureflags/featuredefinition/"),
        )

    def test_inactive_registered_definition_remains_visible_as_fallback(
        self,
    ) -> None:
        self.feature.active = False
        self.feature.save(update_fields=("active", "updated_at"))

        response = self.client.get(
            f"/admin/featureflags/featuredefinition/{self.feature.pk}/change/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Это не означает «выключено»")
