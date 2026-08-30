"""Declarative source of truth for supported feature flags.

Design variants are deliberately fail-closed.  Deploying the application
must never make the prototype public: only a database rule targeting the
``website-design-testers`` group may resolve a design flag to ``v2``.
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

VERSIONS_VARIANTS = ("legacy", "v2")
DEFAULT_VARIANT = "legacy"

DESIGN_FLAG_KEYS = (
    "site_itmocraft_page_version",
    "site_joutak_page_version",
    "site_minigames_page_version",
    "site_contact_page_version",
    "site_header_version",
    "site_footer_version",
)

FEATURE_REGISTRY: dict[str, dict] = {
    "site_itmocraft_page_version": {
        "kind": "variant",
        "default_env": None,
        "default_fallback": DEFAULT_VARIANT,
        "variants": VERSIONS_VARIANTS,
        "pages": ["itmocraft"],
        "sticky": False,
        "description": "Switches the canonical / ITMOcraft page.",
        "visual_impact": "Full ITMOcraft page replacement.",
    },
    "site_joutak_page_version": {
        "kind": "variant",
        "default_env": None,
        "default_fallback": DEFAULT_VARIANT,
        "variants": VERSIONS_VARIANTS,
        "pages": ["joutak"],
        "sticky": False,
        "description": "Switches the /joutak product page.",
        "visual_impact": "Full JouTak page replacement.",
    },
    "site_minigames_page_version": {
        "kind": "variant",
        "default_env": None,
        "default_fallback": DEFAULT_VARIANT,
        "variants": VERSIONS_VARIANTS,
        "pages": ["minigames"],
        "sticky": False,
        "description": "Switches the /minigames product page.",
        "visual_impact": "Full minigames page replacement.",
    },
    "site_contact_page_version": {
        "kind": "variant",
        "default_env": None,
        "default_fallback": DEFAULT_VARIANT,
        "variants": VERSIONS_VARIANTS,
        "pages": ["contact"],
        "sticky": False,
        "description": "Switches the /contact page.",
        "visual_impact": "Full contact page replacement.",
    },
    "site_header_version": {
        "kind": "variant",
        "default_env": None,
        "default_fallback": DEFAULT_VARIANT,
        "variants": VERSIONS_VARIANTS,
        "pages": ["*"],
        "sticky": False,
        "description": "Switches the shared site header.",
        "visual_impact": "Replaces the header on product pages.",
    },
    "site_footer_version": {
        "kind": "variant",
        "default_env": None,
        "default_fallback": DEFAULT_VARIANT,
        "variants": VERSIONS_VARIANTS,
        "pages": ["*"],
        "sticky": False,
        "description": "Switches the shared site footer.",
        "visual_impact": "Replaces the footer on product pages.",
    },
    "profile_personalization_ui": {
        "kind": "boolean",
        "default_env": "FF_PROFILE_PERSONALIZATION_UI",
        "default_fallback": True,
        "variants": (True, False),
        "pages": ["account"],
        "sticky": False,
        "description": "Shows profile personalization UI.",
        "visual_impact": "Shows or hides personalization prompts.",
    },
    "profile_personalization_interstitial": {
        "kind": "boolean",
        "default_env": "FF_PROFILE_PERSONALIZATION_INTERSTITIAL",
        "default_fallback": True,
        "variants": (True, False),
        "pages": ["account"],
        "sticky": False,
        "description": "Shows the post-auth profile interstitial.",
        "visual_impact": "Shows a full-screen profile prompt.",
    },
    "profile_personalization_enforce": {
        "kind": "boolean",
        "default_env": "FF_PROFILE_PERSONALIZATION_ENFORCE",
        "default_fallback": False,
        "variants": (True, False),
        "pages": ["*"],
        "sticky": False,
        "description": "Enforces profile completion for protected actions.",
        "visual_impact": "May reject actions for incomplete profiles.",
    },
}


def get_default_value(key: str) -> bool | str:
    """Resolve a registered default, optionally from an explicit setting."""
    spec = FEATURE_REGISTRY.get(key)
    if spec is None:
        raise KeyError(f"Unknown feature flag: {key}")

    env_var = spec.get("default_env")
    if env_var:
        env_value = getattr(settings, env_var, None)
        if env_value is not None:
            return env_value
    return spec["default_fallback"]


def get_flags_for_page(page: str) -> list[str]:
    return [
        key
        for key, spec in FEATURE_REGISTRY.items()
        if page in spec["pages"] or "*" in spec["pages"]
    ]


def get_valid_variants(key: str) -> tuple[object, ...] | None:
    spec = FEATURE_REGISTRY.get(key)
    if spec is None:
        return None
    return tuple(spec["variants"])


def is_valid_override_value(key: str, value: object) -> bool:
    """Return whether ``value`` is valid; unknown flags fail closed."""
    spec = FEATURE_REGISTRY.get(key)
    if spec is None:
        return False
    if spec["kind"] == "boolean":
        if isinstance(value, bool):
            return True
        return str(value).strip().lower() in {
            "true",
            "false",
            "1",
            "0",
            "yes",
            "no",
            "on",
            "off",
        }
    return str(value) in {str(item) for item in spec["variants"]}


def validate_registry() -> None:
    """Fail startup/deploy sync when registry contracts are inconsistent."""
    for key, spec in FEATURE_REGISTRY.items():
        variants = tuple(spec.get("variants") or ())
        default = get_default_value(key)
        if spec.get("kind") not in {"boolean", "variant"}:
            raise ImproperlyConfigured(f"{key}: unsupported feature kind")
        if not variants or default not in variants:
            raise ImproperlyConfigured(
                f"{key}: default {default!r} is not a valid variant"
            )
        if not spec.get("pages"):
            raise ImproperlyConfigured(f"{key}: pages must not be empty")
        if key in DESIGN_FLAG_KEYS and (
            variants != VERSIONS_VARIANTS
            or default != DEFAULT_VARIANT
            or bool(spec.get("sticky"))
            or spec.get("default_env")
        ):
            raise ImproperlyConfigured(
                f"{key}: design rollout must be legacy-default and non-sticky"
            )


def get_all_keys() -> list[str]:
    return list(FEATURE_REGISTRY)
