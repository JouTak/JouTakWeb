"""
Feature Flag Registry — single source of truth for all feature flags.

Every feature flag in the system should be declared here. This registry:
- Provides human-readable metadata (description, visual_impact)
- Declares valid variants for each flag
- Maps flags to pages they affect
- Enables automatic BFF flag resolution by page
- Enables validation of override values
- Supports ENV variable fallback for defaults

Adding a new feature flag:
    1. Add an entry to FEATURE_REGISTRY below
    2. Run `python manage.py sync_feature_registry` (auto-runs on deploy)
    3. Use <FeatureGate flag="your_flag"> on the frontend
    4. Configure targeting rules in Django admin

Example:
    "itmocraft_new_events": {
        "kind": "boolean",
        "default": False,
        "variants": [True, False],
        "pages": ["itmocraft"],
        "sticky": False,
        "description": "New events section on /itmocraft page",
        "visual_impact": "Adds an events carousel below the header",
    },
"""

from __future__ import annotations

from django.conf import settings

# ─── Registry Definition ────────────────────────────────────────────────────

VERSIONS_VARIANTS = ["legacy", "v2"]
DEFAULT_VARIANT = "legacy"

FEATURE_REGISTRY: dict[str, dict] = {
    # ─── Homepage variant rollout ──────────────────────────────────────
    "site_joutak_page_version": {
        "kind": "variant",
        "default_env": "FF_SITE_HOMEPAGE_VERSION",
        "default_fallback": DEFAULT_VARIANT,
        "variants": VERSIONS_VARIANTS,
        "pages": ["joutak"],
        "sticky": False,
        "description": (
            "Switches the /joutak homepage between versions"
        ),
        "visual_impact": "Full page replacement on /joutak",
    },
    "site_minigames_page_version": {
        "kind": "variant",
        "default_env": "FF_SITE_HOMEPAGE_VERSION",
        "default_fallback": DEFAULT_VARIANT,
        "variants": VERSIONS_VARIANTS,
        "pages": ["minigames"],
        "sticky": False,
        "description": (
            "Switches the /minigames homepage between versions"
        ),
        "visual_impact": "Full page replacement on /minigames",
    },
    "site_homepage_page_version": {
        "kind": "variant",
        "default_env": "FF_SITE_HOMEPAGE_VERSION",
        "default_fallback": DEFAULT_VARIANT,
        "variants": VERSIONS_VARIANTS,
        "pages": ["homepage"],
        "sticky": False,
        "description": (
            "Switches the / homepage between versions"
        ),
        "visual_impact": "Full page replacement on /",
    },
    "site_itmocraft_page_version": {
        "kind": "variant",
        "default_env": "FF_SITE_HOMEPAGE_VERSION",
        "default_fallback": DEFAULT_VARIANT,
        "variants": VERSIONS_VARIANTS,
        "pages": ["itmocraft"],
        "sticky": False,
        "description": (
            "Switches the /itmocraft homepage between versions"
        ),
        "visual_impact": "Full page replacement on /itmocraft",
    },
    # ─── Profile personalization: UI toggle ────────────────────────────
    "profile_personalization_ui": {
        "kind": "boolean",
        "default_env": "FF_PROFILE_PERSONALIZATION_UI",
        "default_fallback": True,
        "variants": [True, False],
        "pages": ["account", "homepage"],
        "sticky": False,
        "description": (
            "Controls whether profile personalization UI elements "
            "(prompts, banners) are shown to users."
        ),
        "visual_impact": "Shows/hides personalization prompts site-wide",
    },
    # ─── Profile personalization: interstitial prompt ──────────────────
    "profile_personalization_interstitial": {
        "kind": "boolean",
        "default_env": "FF_PROFILE_PERSONALIZATION_INTERSTITIAL",
        "default_fallback": True,
        "variants": [True, False],
        "pages": ["account"],
        "sticky": False,
        "description": (
            "Controls the interstitial page that prompts users to "
            "complete their profile after registration/login."
        ),
        "visual_impact": "Full-screen interstitial on login for new users",
    },
    # ─── Profile personalization: enforcement ──────────────────────────
    "profile_personalization_enforce": {
        "kind": "boolean",
        "default_env": "FF_PROFILE_PERSONALIZATION_ENFORCE",
        "default_fallback": False,
        "variants": [True, False],
        "pages": ["*"],
        "sticky": False,
        "description": (
            "When enabled, blocks users with incomplete profiles from "
            "performing certain actions (OAuth linking, etc.)."
        ),
        "visual_impact": "403 error for users without complete profiles",
    },
    # ─── New design elements from website-dev (PR #85) ─────────────────
    "site_footer_version": {
        "kind": "variant",
        "default_env": None,
        "default_fallback": DEFAULT_VARIANT,
        "variants": [True, False],
        "pages": ["*"],
        "sticky": False,
        "description": "New footer design from the website-dev branch.",
        "visual_impact": "Replaces the site footer across all pages",
    },
    "site_header_version": {
        "kind": "variant",
        "default_env": None,
        "default_fallback": DEFAULT_VARIANT,
        "variants": [True, False],
        "pages": ["*"],
        "sticky": False,
        "description": (
            "New header/navigation design from the website-dev branch."
        ),
        "visual_impact": "Replaces the site header/nav across all pages",
    },
    "joutak_new_hero_section": {
        "kind": "boolean",
        "default_env": None,
        "default_fallback": False,
        "variants": [True, False],
        "pages": ["joutak"],
        "sticky": False,
        "description": "Shows the new full-viewport homepage hero.",
        "visual_impact": "Replaces the hero section on /joutak",
    },
    "joutak_new_gallery_section": {
        "kind": "boolean",
        "default_env": None,
        "default_fallback": False,
        "variants": [True, False],
        "pages": ["joutak"],
        "sticky": False,
        "description": "Shows the gallery section on the homepage.",
        "visual_impact": "Photo gallery with tab switching on /joutak",
    },
    "minigames_new_hero_section": {
        "kind": "boolean",
        "default_env": None,
        "default_fallback": False,
        "variants": [True, False],
        "pages": ["minigames"],
        "sticky": False,
        "description": "Shows the new full-viewport homepage hero.",
        "visual_impact": "Replaces the hero section on /minigames",
    },
    "minigames_new_projects_section": {
        "kind": "boolean",
        "default_env": None,
        "default_fallback": False,
        "variants": [True, False],
        "pages": ["minigames"],
        "sticky": False,
        "description": "Shows the new projects section.",
        "visual_impact": "Replaces the hero section on /minigames",
    },
    "minigames_new_gallery_section": {
        "kind": "boolean",
        "default_env": None,
        "default_fallback": False,
        "variants": [True, False],
        "pages": ["minigames"],
        "sticky": False,
        "description": "Shows the new gallery section.",
        "visual_impact": "Replaces the gallery section on /minigames",
    },
    "minigames_new_events_section": {
        "kind": "boolean",
        "default_env": None,
        "default_fallback": False,
        "variants": [True, False],
        "pages": ["minigames"],
        "sticky": False,
        "description": "Shows the new events section.",
        "visual_impact": "Replaces the events section on /minigames",
    },
    "itmocraft_new_hero_section": {
        "kind": "boolean",
        "default_env": None,
        "default_fallback": False,
        "variants": [True, False],
        "pages": ["homepage"],
        "sticky": False,
        "description": "Shows the new full-viewport homepage hero.",
        "visual_impact": "Replaces the hero section on /itmocraft",
    },
    "itmocraft_new_projects_section": {
        "kind": "boolean",
        "default_env": None,
        "default_fallback": False,
        "variants": [True, False],
        "pages": ["homepage"],
        "sticky": False,
        "description": "Shows the new projects section.",
        "visual_impact": "Replaces the hero section on /itmocraft",
    },
    "itmocraft_new_gallery_section": {
        "kind": "boolean",
        "default_env": None,
        "default_fallback": False,
        "variants": [True, False],
        "pages": ["homepage"],
        "sticky": False,
        "description": "Shows the new gallery section.",
        "visual_impact": "Replaces the gallery section on /itmocraft",
    },
    "itmocraft_new_events_section": {
        "kind": "boolean",
        "default_env": None,
        "default_fallback": False,
        "variants": [True, False],
        "pages": ["homepage"],
        "sticky": False,
        "description": "Shows the new events section.",
        "visual_impact": "Replaces the events section on /itmocraft",
    },
    "itmocraft_new_faq_section": {
        "kind": "boolean",
        "default_env": None,
        "default_fallback": False,
        "variants": [True, False],
        "pages": ["homepage"],
        "sticky": False,
        "description": "Shows the new projects section.",
        "visual_impact": "Replaces the FAQ section on /itmocraft",
    },
}


# ─── Helper functions ───────────────────────────────────────────────────────


def get_default_value(key: str) -> bool | str:
    """Resolve the default value for a flag, checking ENV fallback."""
    spec = FEATURE_REGISTRY.get(key)
    if spec is None:
        return False

    env_var = spec.get("default_env")
    if env_var:
        env_value = getattr(settings, env_var, None)
        if env_value is not None:
            return env_value

    return spec["default_fallback"]


def get_flags_for_page(page: str) -> list[str]:
    """Return all flag keys relevant to the given page context."""
    return [
        key
        for key, spec in FEATURE_REGISTRY.items()
        if page in spec["pages"] or "*" in spec["pages"]
    ]


def get_valid_variants(key: str) -> list | None:
    """Return valid variant values for a flag, or None if not in registry."""
    spec = FEATURE_REGISTRY.get(key)
    if spec is None:
        return None
    return spec["variants"]


def is_valid_override_value(key: str, value: str) -> bool:
    """Check if a proposed override value is valid for the given flag."""
    spec = FEATURE_REGISTRY.get(key)
    if spec is None:
        # Unknown flag — allow (may be a DB-only definition)
        return True

    variants = spec["variants"]
    if spec["kind"] == "boolean":
        # Accept common boolean representations
        return value.lower() in {
            "true",
            "false",
            "1",
            "0",
            "yes",
            "no",
            "on",
            "off",
        }
    # For variant flags, check exact match
    return value in [str(v) for v in variants]


def get_all_keys() -> list[str]:
    """Return all registered flag keys."""
    return list(FEATURE_REGISTRY.keys())
