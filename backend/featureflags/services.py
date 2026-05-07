from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from uuid import uuid4

from allauth.headless.contrib.ninja.security import x_session_token_auth
from django.conf import settings
from django.core import signing
from django.http import HttpRequest, HttpResponse
from openfeature import api
from openfeature.evaluation_context import (
    EvaluationContext as OpenFeatureEvaluationContext,
)
from openfeature.flag_evaluation import FlagResolutionDetails, Reason

from featureflags.models import (
    AssignmentSubjectType,
    ExperimentAssignment,
    FeatureDefinition,
    FeatureKind,
    FeatureOverrideScope,
    FeatureRule,
    FeatureRuleType,
)

logger = logging.getLogger(__name__)

FEATURE_OVERRIDE_QUERY_PREFIX = "ff_"
FEATURE_OVERRIDE_CLEAR_QUERY = "ff_clear_overrides"
FEATURE_OVERRIDE_SIGNING_SALT = "featureflags.override_cookie.v1"
DEFAULT_FEATURES = {
    "site_homepage_version": {
        "kind": FeatureKind.VARIANT,
        "default": getattr(settings, "FF_SITE_HOMEPAGE_VERSION", "legacy"),
        "sticky_assignment": False,
    }
}


@dataclass(slots=True, frozen=True)
class OpenFeatureUser:
    """Lightweight stand-in for ``request.user`` used when we rebuild
    a :class:`RequestEvaluationContext` from an OpenFeature evaluation
    context (e.g. inside the OpenFeature provider).

    Intentionally duck-types the fields our rules look at — nothing
    more, nothing less — so we don't accidentally grow a parallel User
    model.
    """

    pk: int
    is_staff: bool = False
    is_authenticated: bool = True


@dataclass(slots=True)
class RequestEvaluationContext:
    request: HttpRequest | None = None
    user: object | None = None
    anonymous_id: str | None = None
    page: str = ""
    request_overrides: dict[str, str] | None = None

    @property
    def user_id(self) -> int | None:
        user = self.user
        if user is None or not getattr(user, "is_authenticated", False):
            return None
        return int(user.pk)

    @property
    def is_staff(self) -> bool:
        user = self.user
        return bool(
            user
            and getattr(user, "is_authenticated", False)
            and getattr(user, "is_staff", False)
        )

    @property
    def has_identity(self) -> bool:
        """True when we can bucket this request deterministically.

        An empty ``identity_key`` (no user, no anonymous cookie) would
        otherwise collapse every anonymous visitor into the same bucket
        and either include or exclude all of them from a percentage
        rollout together, which defeats the point.
        """

        return self.user_id is not None or bool(self.anonymous_id)

    @property
    def identity_key(self) -> str:
        if self.user_id is not None:
            return f"user:{self.user_id}"
        if self.anonymous_id:
            return f"anon:{self.anonymous_id}"
        return ""


@dataclass(slots=True)
class FeatureSpec:
    key: str
    kind: str
    default_value: bool | str
    sticky_assignment: bool = False


def resolve_optional_user(request: HttpRequest) -> object | None:
    user = x_session_token_auth(request)
    if user is not None:
        request.user = user
        return user
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        return user
    return None


def extract_or_create_anonymous_id(request: HttpRequest) -> tuple[str, bool]:
    cookie_name = settings.FEATURE_FLAG_ANONYMOUS_ID_COOKIE
    current = (request.COOKIES.get(cookie_name) or "").strip()
    if current:
        return current, False
    return uuid4().hex, True


def _can_use_request_overrides(user: object | None) -> bool:
    if getattr(settings, "FEATURE_FLAG_OVERRIDE_QUERY_ENABLED", False):
        return True
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_staff", False)
    )


def read_override_cookie(request: HttpRequest) -> dict[str, str]:
    raw = request.COOKIES.get(settings.FEATURE_FLAG_OVERRIDE_COOKIE)
    if not raw:
        return {}
    max_age = getattr(
        settings,
        "FEATURE_FLAG_OVERRIDE_COOKIE_MAX_AGE",
        getattr(
            settings,
            "FEATURE_FLAG_ANONYMOUS_ID_COOKIE_MAX_AGE",
            60 * 60 * 24 * 30,
        ),
    )
    try:
        payload = signing.loads(
            raw,
            salt=FEATURE_OVERRIDE_SIGNING_SALT,
            max_age=max_age,
        )
    except signing.BadSignature:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        str(key): str(value)
        for key, value in payload.items()
        if key and value is not None
    }


def sync_override_cookie(
    request: HttpRequest,
    response: HttpResponse,
    *,
    user: object | None,
) -> dict[str, str]:
    existing = read_override_cookie(request)
    if not _can_use_request_overrides(user):
        return existing

    if request.GET.get(FEATURE_OVERRIDE_CLEAR_QUERY) == "1":
        response.delete_cookie(settings.FEATURE_FLAG_OVERRIDE_COOKIE)
        return {}

    updates = {
        key[len(FEATURE_OVERRIDE_QUERY_PREFIX) :]: value
        for key, value in request.GET.items()
        if key.startswith(FEATURE_OVERRIDE_QUERY_PREFIX) and value
    }
    if not updates:
        return existing

    merged = {**existing, **updates}
    max_age = getattr(
        settings,
        "FEATURE_FLAG_OVERRIDE_COOKIE_MAX_AGE",
        settings.FEATURE_FLAG_ANONYMOUS_ID_COOKIE_MAX_AGE,
    )
    response.set_cookie(
        settings.FEATURE_FLAG_OVERRIDE_COOKIE,
        signing.dumps(merged, salt=FEATURE_OVERRIDE_SIGNING_SALT),
        max_age=max_age,
        httponly=True,
        samesite="Lax",
        secure=not settings.DEBUG,
    )
    return merged


def ensure_anonymous_cookie(
    response: HttpResponse, anonymous_id: str, *, created: bool
) -> None:
    if not created:
        return
    response.set_cookie(
        settings.FEATURE_FLAG_ANONYMOUS_ID_COOKIE,
        anonymous_id,
        max_age=settings.FEATURE_FLAG_ANONYMOUS_ID_COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
        secure=not settings.DEBUG,
    )


def build_context(
    request: HttpRequest,
    *,
    page: str = "",
    response: HttpResponse | None = None,
) -> tuple[RequestEvaluationContext, bool]:
    user = resolve_optional_user(request)
    anonymous_id, created = extract_or_create_anonymous_id(request)
    overrides = (
        read_override_cookie(request)
        if _can_use_request_overrides(user)
        else {}
    )
    if response is not None:
        ensure_anonymous_cookie(response, anonymous_id, created=created)
        overrides = sync_override_cookie(request, response, user=user)
    return (
        RequestEvaluationContext(
            request=request,
            user=user,
            anonymous_id=anonymous_id,
            page=page,
            request_overrides=overrides,
        ),
        created,
    )


def _coerce_value(kind: str, value: object) -> bool | str:
    if kind == FeatureKind.BOOLEAN:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
            "enabled",
        }
    return str(value)


def _reason_for_match(source: str) -> Reason:
    if source == "rule":
        return Reason.TARGETING_MATCH
    if source == "override":
        return Reason.STATIC
    return Reason.DEFAULT


def _bucket_percent(
    identity_key: str, feature_key: str, page: str = ""
) -> int:
    payload = f"{feature_key}:{page}:{identity_key}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return int(digest[:8], 16) % 100


def _rule_matches(
    rule: FeatureRule, context: RequestEvaluationContext
) -> bool:
    if not rule.enabled:
        return False
    if rule.page and rule.page != context.page:
        return False
    user_id = context.user_id
    anonymous_id = context.anonymous_id or ""

    if rule.rule_type == FeatureRuleType.EVERYONE:
        return True
    if rule.rule_type == FeatureRuleType.AUTHENTICATED:
        return user_id is not None
    if rule.rule_type == FeatureRuleType.STAFF:
        return context.is_staff
    if rule.rule_type == FeatureRuleType.USER_ALLOWLIST:
        return user_id is not None and str(user_id) in {
            str(v) for v in rule.actor_ids
        }
    if rule.rule_type == FeatureRuleType.USER_DENYLIST:
        return user_id is not None and str(user_id) in {
            str(v) for v in rule.actor_ids
        }
    if rule.rule_type == FeatureRuleType.ANONYMOUS_ALLOWLIST:
        return anonymous_id and anonymous_id in {
            str(v) for v in rule.actor_ids
        }
    if rule.rule_type == FeatureRuleType.ANONYMOUS_DENYLIST:
        return anonymous_id and anonymous_id in {
            str(v) for v in rule.actor_ids
        }
    if rule.rule_type == FeatureRuleType.PERCENTAGE:
        # Without a stable identity we'd bucket every anonymous visitor
        # identically, i.e. either flip the rule on for all of them at
        # once or leave everyone out — both of which break the point of
        # a percentage rollout. Treat as non-match instead.
        if not context.has_identity:
            return False
        percentage = max(0, min(int(rule.percentage or 0), 100))
        return (
            _bucket_percent(
                context.identity_key, rule.feature.key, context.page
            )
            < percentage
        )
    logger.warning(
        "featureflags: unknown rule_type %r on feature %s (rule id=%s)",
        rule.rule_type,
        rule.feature.key,
        rule.pk,
    )
    return False


def _rule_result(rule: FeatureRule) -> str:
    if rule.rule_type in {
        FeatureRuleType.USER_DENYLIST,
        FeatureRuleType.ANONYMOUS_DENYLIST,
    }:
        return rule.feature.default_value
    return rule.value


def _db_override(
    feature: FeatureDefinition,
    context: RequestEvaluationContext,
) -> str | None:
    for override in feature.overrides.filter(enabled=True):
        if override.scope_type == FeatureOverrideScope.GLOBAL:
            return override.value
        if (
            override.scope_type == FeatureOverrideScope.USER
            and context.user_id is not None
            and override.scope_value == str(context.user_id)
        ):
            return override.value
        if (
            override.scope_type == FeatureOverrideScope.ANONYMOUS
            and context.anonymous_id
            and override.scope_value == context.anonymous_id
        ):
            return override.value
    return None


def _definition_for_key(key: str) -> FeatureDefinition | None:
    return (
        FeatureDefinition.objects.prefetch_related("rules", "overrides")
        .filter(key=key, active=True)
        .first()
    )


def get_feature_spec(key: str) -> FeatureSpec | None:
    feature = _definition_for_key(key)
    if feature is not None:
        return FeatureSpec(
            key=feature.key,
            kind=feature.kind,
            default_value=_coerce_value(feature.kind, feature.default_value),
            sticky_assignment=feature.sticky_assignment,
        )

    default_spec = DEFAULT_FEATURES.get(key)
    if default_spec is None:
        return None

    return FeatureSpec(
        key=key,
        kind=default_spec["kind"],
        default_value=_coerce_value(
            default_spec["kind"],
            default_spec["default"],
        ),
        sticky_assignment=bool(default_spec.get("sticky_assignment", False)),
    )


def _assignment_subject(
    context: RequestEvaluationContext,
) -> tuple[str, str] | None:
    if context.user_id is not None:
        return AssignmentSubjectType.USER, str(context.user_id)
    if context.anonymous_id:
        return AssignmentSubjectType.ANONYMOUS, context.anonymous_id
    return None


def _sticky_assignment(
    feature: FeatureDefinition,
    context: RequestEvaluationContext,
) -> str | None:
    subject = _assignment_subject(context)
    if not feature.sticky_assignment or subject is None:
        return None
    subject_type, subject_key = subject
    assignment = feature.assignments.filter(
        subject_type=subject_type,
        subject_key=subject_key,
        page=context.page,
    ).first()
    return assignment.value if assignment else None


def _persist_assignment(
    feature: FeatureDefinition, context: RequestEvaluationContext, value: str
) -> None:
    subject = _assignment_subject(context)
    if not feature.sticky_assignment or subject is None:
        return
    subject_type, subject_key = subject
    ExperimentAssignment.objects.update_or_create(
        feature=feature,
        subject_type=subject_type,
        subject_key=subject_key,
        page=context.page,
        defaults={"value": value},
    )


def _evaluate_definition(
    feature: FeatureDefinition,
    context: RequestEvaluationContext,
) -> tuple[bool | str, Reason, str | None]:
    overrides = context.request_overrides or {}
    if feature.key in overrides:
        value = _coerce_value(feature.kind, overrides[feature.key])
        return value, _reason_for_match("override"), str(value)

    db_override = _db_override(feature, context)
    if db_override is not None:
        value = _coerce_value(feature.kind, db_override)
        return value, _reason_for_match("override"), str(value)

    sticky_value = _sticky_assignment(feature, context)
    if sticky_value is not None:
        value = _coerce_value(feature.kind, sticky_value)
        return value, Reason.CACHED, str(value)

    for rule in feature.rules.all():
        if _rule_matches(rule, context):
            value = _rule_result(rule)
            _persist_assignment(feature, context, value)
            coerced = _coerce_value(feature.kind, value)
            return coerced, _reason_for_match("rule"), str(coerced)

    default_value = _coerce_value(feature.kind, feature.default_value)
    return default_value, Reason.DEFAULT, str(default_value)


def to_openfeature_context(
    context: RequestEvaluationContext,
) -> OpenFeatureEvaluationContext:
    identity_key = context.identity_key
    attributes = {
        "user_id": context.user_id,
        "anonymous_id": context.anonymous_id,
        "page": context.page,
        "is_staff": context.is_staff,
        "identity_key": identity_key or None,
        "overrides": context.request_overrides or {},
    }
    return OpenFeatureEvaluationContext(
        targeting_key=identity_key or None,
        attributes={
            key: value
            for key, value in attributes.items()
            if value is not None
        },
    )


def from_openfeature_context(
    evaluation_context: OpenFeatureEvaluationContext | None,
) -> RequestEvaluationContext:
    attrs = dict(evaluation_context.attributes) if evaluation_context else {}
    targeting_key = (
        evaluation_context.targeting_key if evaluation_context else None
    )
    identity_key = str(targeting_key or attrs.get("identity_key") or "")
    user_id = attrs.get("user_id")
    anonymous_id = attrs.get("anonymous_id")
    if anonymous_id is None and identity_key.startswith("anon:"):
        anonymous_id = identity_key.split(":", 1)[1]
    raw_overrides = attrs.get("overrides") or {}
    request_overrides = (
        {
            str(key): str(value)
            for key, value in dict(raw_overrides).items()
        }
        if isinstance(raw_overrides, dict)
        else {}
    )

    user: OpenFeatureUser | None = None
    if user_id is not None:
        try:
            user = OpenFeatureUser(
                pk=int(user_id),
                is_staff=bool(attrs.get("is_staff", False)),
            )
        except (TypeError, ValueError):
            user = None

    return RequestEvaluationContext(
        user=user,
        anonymous_id=str(anonymous_id) if anonymous_id else None,
        page=str(attrs.get("page") or ""),
        request_overrides=request_overrides,
    )


def resolve_flag_details(
    flag_key: str,
    kind: str,
    default_value: bool | str,
    evaluation_context: OpenFeatureEvaluationContext | None = None,
) -> FlagResolutionDetails[bool | str]:
    feature = _definition_for_key(flag_key)
    if feature is None:
        return FlagResolutionDetails(
            value=default_value,
            reason=Reason.DEFAULT,
            variant=str(default_value),
        )

    request_context = from_openfeature_context(evaluation_context)
    value, reason, variant = _evaluate_definition(feature, request_context)
    return FlagResolutionDetails(
        value=value,
        reason=reason,
        variant=variant,
    )


def evaluate_many(
    context: RequestEvaluationContext,
    keys: list[str] | tuple[str, ...],
) -> dict[str, bool | str]:
    client = api.get_client()
    evaluation_context = to_openfeature_context(context)
    resolved: dict[str, bool | str] = {}
    for key in keys:
        spec = get_feature_spec(key)
        if spec is None:
            resolved[key] = False
            continue
        if spec.kind == FeatureKind.BOOLEAN:
            resolved[key] = client.get_boolean_value(
                key,
                bool(spec.default_value),
                evaluation_context=evaluation_context,
            )
            continue
        resolved[key] = client.get_string_value(
            key,
            str(spec.default_value),
            evaluation_context=evaluation_context,
        )
    return resolved


def seed_homepage_feature() -> None:
    spec = DEFAULT_FEATURES["site_homepage_version"]
    FeatureDefinition.objects.get_or_create(
        key="site_homepage_version",
        defaults={
            "description": "Homepage version rollout for /joutak",
            "kind": spec["kind"],
            "default_value": str(spec["default"]),
            "active": True,
            "sticky_assignment": bool(spec["sticky_assignment"]),
        },
    )
