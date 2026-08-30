from django.test import SimpleTestCase

from featureflags.registry import (
    DESIGN_FLAG_KEYS,
    FEATURE_REGISTRY,
    get_default_value,
    get_flags_for_page,
)


class FeatureRegistryTests(SimpleTestCase):
    def test_contact_page_flag_is_closed_non_sticky_design_variant(self):
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
        self.assertIn(key, get_flags_for_page("contact"))
