from __future__ import annotations

from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from featureflags.registry import (
    CONTACT_PAGE_ROLLOUT_POLICY,
    DESIGN_FLAG_KEYS,
    DESIGN_ROLLOUT_POLICY,
    DESIGN_TESTER_GROUP_SLUG,
    FEATURE_REGISTRY,
    GUIDED_ROLLOUT_AUDIENCES,
    canonical_variant_token,
    get_allowed_audiences,
    get_default_value,
    get_flags_for_page,
    get_required_group_slug,
    get_variant_choices,
    is_audience_allowed,
    is_public_rollout_allowed,
    validate_registry,
)


class FeatureRegistryPolicyTests(SimpleTestCase):
    def test_contact_page_flag_has_explicit_public_rollout_policy(self):
        key = "site_contact_page_version"

        self.assertIn(key, DESIGN_FLAG_KEYS)
        spec = FEATURE_REGISTRY[key]
        self.assertEqual(spec["kind"], "variant")
        self.assertIsNone(spec["default_env"])
        self.assertEqual(spec["default_fallback"], "legacy")
        self.assertEqual(get_default_value(key), "legacy")
        self.assertEqual(spec["variants"], ("legacy", "v2"))
        self.assertEqual(spec["pages"], ["contact"])
        self.assertFalse(spec["sticky"])
        self.assertIs(
            spec["rollout_policy"],
            CONTACT_PAGE_ROLLOUT_POLICY,
        )
        self.assertIsNot(
            CONTACT_PAGE_ROLLOUT_POLICY,
            DESIGN_ROLLOUT_POLICY,
        )
        self.assertEqual(get_allowed_audiences(key), ("group", "everyone"))
        self.assertEqual(
            get_required_group_slug(key),
            DESIGN_TESTER_GROUP_SLUG,
        )
        self.assertEqual(CONTACT_PAGE_ROLLOUT_POLICY.guarded_value, "v2")
        self.assertEqual(CONTACT_PAGE_ROLLOUT_POLICY.safe_default, "legacy")
        self.assertTrue(CONTACT_PAGE_ROLLOUT_POLICY.allow_staff_preview)
        self.assertFalse(CONTACT_PAGE_ROLLOUT_POLICY.allow_sticky)
        self.assertTrue(is_public_rollout_allowed(key))
        self.assertIn(key, get_flags_for_page("contact"))

    def test_other_design_flags_remain_group_only(self) -> None:
        private_keys = (
            "site_itmocraft_page_version",
            "site_joutak_page_version",
            "site_minigames_page_version",
            "site_header_version",
            "site_footer_version",
        )

        for key in private_keys:
            with self.subTest(key=key):
                self.assertIs(
                    FEATURE_REGISTRY[key]["rollout_policy"],
                    DESIGN_ROLLOUT_POLICY,
                )
                self.assertEqual(get_allowed_audiences(key), ("group",))
                self.assertEqual(
                    get_required_group_slug(key),
                    DESIGN_TESTER_GROUP_SLUG,
                )
                self.assertFalse(is_audience_allowed(key, "everyone"))
                self.assertFalse(is_public_rollout_allowed(key))

    def test_contact_is_only_guarded_flag_allowing_public_rollout(
        self,
    ) -> None:
        for key in DESIGN_FLAG_KEYS:
            with self.subTest(key=key):
                self.assertEqual(
                    is_public_rollout_allowed(key),
                    key == "site_contact_page_version",
                )

    def test_regular_flags_expose_guided_audiences(self) -> None:
        key = "profile_personalization_ui"

        self.assertEqual(
            get_allowed_audiences(key),
            GUIDED_ROLLOUT_AUDIENCES,
        )
        self.assertIsNone(get_required_group_slug(key))

    def test_unknown_flag_never_allows_an_audience(self) -> None:
        self.assertFalse(is_audience_allowed("unknown", "everyone"))

    def test_variant_labels_come_from_policy_metadata(self) -> None:
        self.assertEqual(
            get_variant_choices("profile_personalization_ui"),
            (
                ("true", "Включено (true)"),
                ("false", "Выключено (false)"),
            ),
        )

    def test_boolean_tokens_are_case_insensitive_and_canonical(self) -> None:
        for value in (True, "True", " TRUE ", "1", "yes", "ON"):
            with self.subTest(value=value):
                self.assertEqual(canonical_variant_token(value), "true")
        for value in (False, "False", " FALSE ", "0", "no", "OFF"):
            with self.subTest(value=value):
                self.assertEqual(canonical_variant_token(value), "false")
        self.assertEqual(
            get_variant_choices("site_header_version"),
            (
                ("legacy", "Текущая версия (legacy)"),
                ("v2", "Новая версия (v2)"),
            ),
        )

    def test_registry_validation_rejects_guarded_key_snapshot_drift(self):
        key = "profile_personalization_ui"
        drifted_spec = {
            **FEATURE_REGISTRY[key],
            "rollout_policy": DESIGN_ROLLOUT_POLICY,
        }

        with (
            patch.dict(FEATURE_REGISTRY, {key: drifted_spec}),
            self.assertRaises(ImproperlyConfigured),
        ):
            validate_registry()

    def test_registry_validation_requires_operator_presentation(self) -> None:
        key = "profile_personalization_ui"
        for field in ("title", "description", "visual_impact"):
            with self.subTest(field=field):
                invalid_spec = {**FEATURE_REGISTRY[key], field: ""}
                with (
                    patch.dict(FEATURE_REGISTRY, {key: invalid_spec}),
                    self.assertRaises(ImproperlyConfigured),
                ):
                    validate_registry()
