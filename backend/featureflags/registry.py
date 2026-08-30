"""Declarative source of truth for supported feature flags.

Design variants are deliberately fail-closed.  Deploying the application
must never make the prototype public: only a database rule targeting the
``website-design-testers`` group may resolve a design flag to ``v2``.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

VERSIONS_VARIANTS = ("legacy", "v2")
DEFAULT_VARIANT = "legacy"

DESIGN_TESTER_GROUP_SLUG = "website-design-testers"

# These values intentionally match ``FeatureRuleType`` without importing
# models here (the models themselves import this registry).  Raw operational
# rules can still represent deny/anonymous cases, while the guided rollout UI
# only exposes the audiences that are understandable and safe for day-to-day
# use.
GUIDED_ROLLOUT_AUDIENCES = (
    "group",
    "user_allowlist",
    "staff",
    "authenticated",
    "percentage",
    "everyone",
)


@dataclass(frozen=True, slots=True)
class RolloutPolicy:
    """Runtime and operator constraints for one registry entry."""

    allowed_audiences: tuple[str, ...]
    required_group_slug: str | None = None
    guarded_value: bool | str | None = None
    safe_default: bool | str | None = None
    allow_staff_preview: bool = True
    allow_public: bool = True
    allow_sticky: bool = True
    variant_labels: tuple[tuple[bool | str, str], ...] = ()


DEFAULT_ROLLOUT_POLICY = RolloutPolicy(
    allowed_audiences=GUIDED_ROLLOUT_AUDIENCES,
)
BOOLEAN_ROLLOUT_POLICY = RolloutPolicy(
    allowed_audiences=GUIDED_ROLLOUT_AUDIENCES,
    variant_labels=(
        (True, "Включено (true)"),
        (False, "Выключено (false)"),
    ),
)
DESIGN_ROLLOUT_POLICY = RolloutPolicy(
    allowed_audiences=("group",),
    required_group_slug=DESIGN_TESTER_GROUP_SLUG,
    guarded_value="v2",
    safe_default=DEFAULT_VARIANT,
    allow_staff_preview=True,
    allow_public=False,
    allow_sticky=False,
    variant_labels=(
        ("legacy", "Текущая версия (legacy)"),
        ("v2", "Новая версия (v2)"),
    ),
)

PERSONALIZATION_FLAG_KEYS = (
    "profile_personalization_ui",
    "profile_personalization_interstitial",
    "profile_personalization_enforce",
)

FEATURE_REGISTRY: dict[str, dict] = {
    "site_itmocraft_page_version": {
        "title": "Страница ITMOcraft",
        "kind": "variant",
        "default_env": None,
        "default_fallback": DEFAULT_VARIANT,
        "variants": VERSIONS_VARIANTS,
        "pages": ["itmocraft"],
        "sticky": False,
        "description": "Переключает основную страницу ITMOcraft.",
        "visual_impact": "Полностью заменяет содержимое страницы ITMOcraft.",
        "rollout_policy": DESIGN_ROLLOUT_POLICY,
    },
    "site_joutak_page_version": {
        "title": "Страница JouTak",
        "kind": "variant",
        "default_env": None,
        "default_fallback": DEFAULT_VARIANT,
        "variants": VERSIONS_VARIANTS,
        "pages": ["joutak"],
        "sticky": False,
        "description": "Переключает страницу продукта JouTak.",
        "visual_impact": "Полностью заменяет содержимое страницы JouTak.",
        "rollout_policy": DESIGN_ROLLOUT_POLICY,
    },
    "site_minigames_page_version": {
        "title": "Страница мини-игр",
        "kind": "variant",
        "default_env": None,
        "default_fallback": DEFAULT_VARIANT,
        "variants": VERSIONS_VARIANTS,
        "pages": ["minigames"],
        "sticky": False,
        "description": "Переключает страницу мини-игр.",
        "visual_impact": "Полностью заменяет содержимое страницы мини-игр.",
        "rollout_policy": DESIGN_ROLLOUT_POLICY,
    },
    "site_contact_page_version": {
        "title": "Страница контактов",
        "kind": "variant",
        "default_env": None,
        "default_fallback": DEFAULT_VARIANT,
        "variants": VERSIONS_VARIANTS,
        "pages": ["contact"],
        "sticky": False,
        "description": "Переключает страницу контактов.",
        "visual_impact": "Полностью заменяет содержимое страницы контактов.",
        "rollout_policy": DESIGN_ROLLOUT_POLICY,
    },
    "site_header_version": {
        "title": "Шапка сайта",
        "kind": "variant",
        "default_env": None,
        "default_fallback": DEFAULT_VARIANT,
        "variants": VERSIONS_VARIANTS,
        "pages": ["*"],
        "sticky": False,
        "description": "Переключает общую шапку сайта.",
        "visual_impact": "Заменяет шапку на продуктовых страницах.",
        "rollout_policy": DESIGN_ROLLOUT_POLICY,
    },
    "site_footer_version": {
        "title": "Подвал сайта",
        "kind": "variant",
        "default_env": None,
        "default_fallback": DEFAULT_VARIANT,
        "variants": VERSIONS_VARIANTS,
        "pages": ["*"],
        "sticky": False,
        "description": "Переключает общий подвал сайта.",
        "visual_impact": "Заменяет подвал на продуктовых страницах.",
        "rollout_policy": DESIGN_ROLLOUT_POLICY,
    },
    "profile_personalization_ui": {
        "title": "Персонализация профиля",
        "kind": "boolean",
        "default_env": "FF_PROFILE_PERSONALIZATION_UI",
        "default_fallback": True,
        "variants": (True, False),
        "pages": ["account"],
        "sticky": False,
        "description": "Показывает интерфейс персонализации профиля.",
        "visual_impact": "Показывает или скрывает подсказки персонализации.",
        "rollout_policy": BOOLEAN_ROLLOUT_POLICY,
    },
    "profile_personalization_interstitial": {
        "title": "Экран персонализации после входа",
        "kind": "boolean",
        "default_env": "FF_PROFILE_PERSONALIZATION_INTERSTITIAL",
        "default_fallback": True,
        "variants": (True, False),
        "pages": ["account"],
        "sticky": False,
        "description": "Показывает экран персонализации после входа.",
        "visual_impact": (
            "Показывает полноэкранное предложение заполнить профиль."
        ),
        "rollout_policy": BOOLEAN_ROLLOUT_POLICY,
    },
    "profile_personalization_enforce": {
        "title": "Обязательное заполнение профиля",
        "kind": "boolean",
        "default_env": "FF_PROFILE_PERSONALIZATION_ENFORCE",
        "default_fallback": False,
        "variants": (True, False),
        "pages": ["*"],
        "sticky": False,
        "description": "Требует заполнить профиль для защищённых действий.",
        "visual_impact": "Может блокировать действия до заполнения профиля.",
        "rollout_policy": BOOLEAN_ROLLOUT_POLICY,
    },
}


def _derived_guarded_keys() -> tuple[str, ...]:
    return tuple(
        key
        for key, spec in FEATURE_REGISTRY.items()
        if spec.get("rollout_policy", DEFAULT_ROLLOUT_POLICY).guarded_value
        is not None
    )


# Compatibility export for callers that still need the complete collection.
# Runtime decisions use each entry's policy directly, not this snapshot.
DESIGN_FLAG_KEYS = _derived_guarded_keys()


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


def get_feature_title(key: str) -> str:
    spec = FEATURE_REGISTRY.get(key)
    if spec is None:
        raise KeyError(f"Unknown feature flag: {key}")
    return str(spec.get("title") or key)


def canonical_variant_token(value: object) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return "true"
        if normalized in {"false", "0", "no", "off"}:
            return "false"
        return value.strip()
    return str(value)


def get_rollout_policy(key: str) -> RolloutPolicy:
    """Return the guided-rollout policy for a registered flag."""
    spec = FEATURE_REGISTRY.get(key)
    if spec is None:
        raise KeyError(f"Unknown feature flag: {key}")
    return spec.get("rollout_policy", DEFAULT_ROLLOUT_POLICY)


def get_allowed_audiences(key: str) -> tuple[str, ...]:
    return get_rollout_policy(key).allowed_audiences


def is_audience_allowed(key: str, audience: str) -> bool:
    try:
        return str(audience) in get_allowed_audiences(key)
    except KeyError:
        return False


def get_required_group_slug(key: str) -> str | None:
    return get_rollout_policy(key).required_group_slug


def is_staff_preview_allowed(key: str) -> bool:
    try:
        return get_rollout_policy(key).allow_staff_preview
    except KeyError:
        return False


def is_public_rollout_allowed(key: str) -> bool:
    try:
        return get_rollout_policy(key).allow_public
    except KeyError:
        return False


def get_variant_choices(key: str) -> tuple[tuple[str, str], ...]:
    """Return canonical values and human labels from registry policy."""
    spec = FEATURE_REGISTRY.get(key)
    if spec is None:
        return ()
    labels = {
        canonical_variant_token(value): label
        for value, label in get_rollout_policy(key).variant_labels
    }
    return tuple(
        (token, labels.get(token, token))
        for token in (
            canonical_variant_token(value) for value in spec["variants"]
        )
    )


def is_guarded_flag(key: str) -> bool:
    try:
        return get_rollout_policy(key).guarded_value is not None
    except KeyError:
        return False


def is_design_flag(key: str) -> bool:
    """Compatibility name for policy-guarded design variants."""
    return is_guarded_flag(key)


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
    if DESIGN_FLAG_KEYS != _derived_guarded_keys():
        raise ImproperlyConfigured(
            "guarded feature keys drifted from rollout policy metadata"
        )
    for key, spec in FEATURE_REGISTRY.items():
        variants = tuple(spec.get("variants") or ())
        variant_tokens = {canonical_variant_token(value) for value in variants}
        default = get_default_value(key)
        if spec.get("kind") not in {"boolean", "variant"}:
            raise ImproperlyConfigured(f"{key}: unsupported feature kind")
        if not str(spec.get("title") or "").strip():
            raise ImproperlyConfigured(f"{key}: operator title is required")
        for metadata_field in ("description", "visual_impact"):
            if not str(spec.get(metadata_field) or "").strip():
                raise ImproperlyConfigured(
                    f"{key}: operator {metadata_field} is required"
                )
        if not variants or default not in variants:
            raise ImproperlyConfigured(
                f"{key}: default {default!r} is not a valid variant"
            )
        if not spec.get("pages"):
            raise ImproperlyConfigured(f"{key}: pages must not be empty")
        policy = get_rollout_policy(key)
        if not policy.allowed_audiences or not set(
            policy.allowed_audiences
        ).issubset(GUIDED_ROLLOUT_AUDIENCES):
            raise ImproperlyConfigured(
                f"{key}: rollout policy contains unsupported audiences"
            )
        if policy.allow_public != ("everyone" in policy.allowed_audiences):
            raise ImproperlyConfigured(
                f"{key}: public rollout policy contradicts audiences"
            )
        if (
            policy.required_group_slug
            and "group" not in policy.allowed_audiences
        ):
            raise ImproperlyConfigured(
                f"{key}: required group audience is not allowed"
            )
        label_tokens = {
            canonical_variant_token(value)
            for value, _label in policy.variant_labels
        }
        if policy.variant_labels and label_tokens != variant_tokens:
            raise ImproperlyConfigured(
                f"{key}: policy labels must cover every variant"
            )
        if policy.guarded_value is not None:
            guarded_token = canonical_variant_token(policy.guarded_value)
            safe_token = canonical_variant_token(policy.safe_default)
            if (
                policy.safe_default is None
                or guarded_token not in variant_tokens
                or safe_token not in variant_tokens
                or guarded_token == safe_token
            ):
                raise ImproperlyConfigured(
                    f"{key}: guarded rollout values are inconsistent"
                )
            if (
                canonical_variant_token(default) != safe_token
                or (bool(spec.get("sticky")) and not policy.allow_sticky)
                or spec.get("default_env")
            ):
                raise ImproperlyConfigured(
                    f"{key}: guarded rollout default can drift unsafe"
                )
        if policy == DESIGN_ROLLOUT_POLICY and variants != VERSIONS_VARIANTS:
            raise ImproperlyConfigured(
                f"{key}: design rollout variants must be legacy and v2"
            )


def get_all_keys() -> list[str]:
    return list(FEATURE_REGISTRY)
