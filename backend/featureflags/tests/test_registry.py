from __future__ import annotations

from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from featureflags.registry import (
    DESIGN_ROLLOUT_POLICY,
    DESIGN_TESTER_GROUP_SLUG,
    FEATURE_REGISTRY,
    GUIDED_ROLLOUT_AUDIENCES,
    get_allowed_audiences,
    get_required_group_slug,
    get_variant_choices,
    is_audience_allowed,
    validate_registry,
)


class FeatureRegistryPolicyTests(SimpleTestCase):
    def test_design_flags_only_allow_the_canonical_group(self) -> None:
        key = "site_itmocraft_page_version"

        self.assertEqual(get_allowed_audiences(key), ("group",))
        self.assertEqual(
            get_required_group_slug(key),
            DESIGN_TESTER_GROUP_SLUG,
        )
        self.assertFalse(is_audience_allowed(key, "everyone"))

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
