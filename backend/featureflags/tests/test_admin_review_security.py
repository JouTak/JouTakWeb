from __future__ import annotations

from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase

from featureflags.admin import (
    _review_token_is_valid,
    _sign_review,
    rollout_add_view,
)
from featureflags.admin_services import start_rollout
from featureflags.forms import GuidedRolloutForm, RolloutAudience
from featureflags.models import (
    FeatureDefinition,
    FeatureRule,
    FeatureRuleType,
)

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


class RolloutReviewTokenSecurityTests(TestCase):
    def setUp(self) -> None:
        self.operator = User.objects.create_user(
            username="review-operator",
            password="StrongPass123!",
            is_staff=True,
        )
        self.other_operator = User.objects.create_user(
            username="other-review-operator",
            password="StrongPass123!",
            is_staff=True,
        )
        self.feature = FeatureDefinition.objects.create(
            key="profile_personalization_enforce",
            kind="boolean",
            default_value="false",
        )
        form = GuidedRolloutForm(
            data={
                "feature": self.feature.pk,
                "value": "true",
                "page": "",
                "audience": RolloutAudience.STAFF,
                "reason": "Review token security check",
                "enabled": "on",
            },
            request_user=self.operator,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.cleaned_data = form.cleaned_data

    def test_token_is_bound_to_user_and_all_reviewed_values(self) -> None:
        token = _sign_review(self.cleaned_data, user=self.operator)

        self.assertTrue(
            _review_token_is_valid(
                token,
                self.cleaned_data,
                user=self.operator,
            )
        )
        self.assertFalse(
            _review_token_is_valid(
                token,
                self.cleaned_data,
                user=self.other_operator,
            )
        )
        changed = {
            **self.cleaned_data,
            "reason": "A different unreviewed reason",
        }
        self.assertFalse(
            _review_token_is_valid(token, changed, user=self.operator)
        )

    def test_tampered_token_is_rejected(self) -> None:
        token = _sign_review(self.cleaned_data, user=self.operator)

        self.assertFalse(
            _review_token_is_valid(
                f"{token}tampered",
                self.cleaned_data,
                user=self.operator,
            )
        )

    def test_token_expires_after_review_window(self) -> None:
        with patch("django.core.signing.time.time", return_value=1_000):
            token = _sign_review(self.cleaned_data, user=self.operator)

        with patch("django.core.signing.time.time", return_value=1_901):
            self.assertFalse(
                _review_token_is_valid(
                    token,
                    self.cleaned_data,
                    user=self.operator,
                )
            )

    def test_invalid_review_post_returns_form_without_signing(self) -> None:
        grant(
            self.operator,
            "featureflags.add_featurerule",
            "featureflags.view_featuredefinition",
            "featureflags.view_featuregroup",
            "featureflags.view_featurerule",
        )
        request = RequestFactory().post(
            "/admin/featureflags/rollouts/new/",
            {
                "feature": self.feature.pk,
                "value": "true",
                "page": "",
                "audience": RolloutAudience.STAFF,
                "enabled": "on",
                "_review": "1",
            },
        )
        request.user = self.operator
        request._dont_enforce_csrf_checks = True

        response = rollout_add_view(request, admin_site=admin.site)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context_data["review"])
        self.assertEqual(response.context_data["review_token"], "")
        self.assertIn("reason", response.context_data["form"].errors)
        self.assertFalse(
            FeatureDefinition.objects.get(pk=self.feature.pk).rules.exists()
        )

    def test_missing_confirmation_preserves_review_and_token(self) -> None:
        grant(
            self.operator,
            "featureflags.add_featurerule",
            "featureflags.view_featuredefinition",
            "featureflags.view_featuregroup",
            "featureflags.view_featurerule",
        )
        token = _sign_review(self.cleaned_data, user=self.operator)
        request = RequestFactory().post(
            "/admin/featureflags/rollouts/new/",
            {
                "feature": self.feature.pk,
                "value": "true",
                "page": "",
                "audience": RolloutAudience.STAFF,
                "reason": "Review token security check",
                "enabled": "on",
                "review_token": token,
                "_create": "1",
            },
        )
        request.user = self.operator
        request._dont_enforce_csrf_checks = True

        response = rollout_add_view(request, admin_site=admin.site)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data["review"])
        self.assertEqual(response.context_data["review_token"], token)
        self.assertIn("confirm_rollout", response.context_data["form"].errors)
        self.assertFalse(self.feature.rules.exists())

    def test_global_rollout_conflicts_with_page_specific_rule(self) -> None:
        FeatureRule.objects.create(
            feature=self.feature,
            name="Existing account rule",
            rule_type=FeatureRuleType.STAFF,
            value="true",
            page="account",
        )

        form = GuidedRolloutForm(
            data={
                "feature": self.feature.pk,
                "value": "true",
                "page": "",
                "audience": RolloutAudience.STAFF,
                "reason": "Overlapping rollout check",
                "enabled": "on",
            },
            request_user=self.operator,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("пересекающийся", str(form.non_field_errors()))

    def test_start_draft_rechecks_overlapping_page_scope(self) -> None:
        FeatureRule.objects.create(
            feature=self.feature,
            name="Existing account rule",
            rule_type=FeatureRuleType.STAFF,
            value="true",
            page="account",
        )
        draft = FeatureRule.objects.create(
            feature=self.feature,
            name="Global draft",
            rule_type=FeatureRuleType.STAFF,
            value="true",
            page="",
            enabled=False,
        )

        with self.assertRaisesMessage(ValidationError, "активный раскат"):
            start_rollout(
                rule_id=draft.pk,
                user=self.operator,
                reason="Attempt overlapping start",
            )

        draft.refresh_from_db()
        self.assertFalse(draft.enabled)

    def test_guided_form_exposes_registry_empty_state(self) -> None:
        FeatureDefinition.objects.update(active=False)

        form = GuidedRolloutForm(request_user=self.operator)

        self.assertTrue(form.registry_empty)
        self.assertFalse(form.fields["feature"].queryset.exists())
