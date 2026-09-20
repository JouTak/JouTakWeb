from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import secrets
import time
from dataclasses import dataclass
from types import MappingProxyType

from accounts.services.admin_mfa import (
    SESSION_KEY_ADMIN_MFA_PENDING,
    AdminMFARateLimitError,
    get_pending_admin_login,
    register_admin_webauthn_boundary_failure,
)
from accounts.webauthn import (
    WEBAUTHN_CHALLENGE_SESSION_KEY,
    WEBAUTHN_CREATE,
    WEBAUTHN_GET,
    WEBAUTHN_SESSION_BINDING_KEY,
    WebAuthnClientDataError,
    WebAuthnStateError,
    require_webauthn_user_verification,
    validate_webauthn_client_data,
    webauthn_challenge_digest,
)
from allauth.headless import app_settings as headless_app_settings
from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.backends.base import SessionBase
from django.core.cache import caches
from django.core.exceptions import DisallowedHost, RequestDataTooBig
from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
    RawPostDataException,
)
from django.utils.cache import patch_cache_control

logger = logging.getLogger(__name__)

ACCOUNT_SURFACE = "account"
ADMIN_SURFACE = "admin"
_GENERIC_ERROR = "Invalid WebAuthn response."
_ACCOUNT_LOGIN_SESSION_KEY = "account_login"
_METADATA_VERSION = 1
_CLAIM_CACHE_PREFIX = "webauthn:challenge:claimed:"
_SHA256_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_ORIGIN_REJECTION_REASONS = frozenset(
    {
        "cross_origin_not_allowed",
        "invalid_cross_origin_flag",
        "origin_not_allowed",
        "origin_policy_not_configured",
    }
)


@dataclass(frozen=True, slots=True)
class _CeremonyPolicy:
    method: str
    expected_type: str
    surface: str
    nested_credential: bool
    purpose: str


@dataclass(frozen=True, slots=True)
class _BoundarySession:
    store: SessionBase
    external: bool


class _ChallengeBoundaryError(ValueError):
    def __init__(self, reason_code: str):
        self.reason_code = reason_code
        super().__init__("Invalid WebAuthn challenge state.")


def _build_completion_policies() -> MappingProxyType:
    policies: dict[str, _CeremonyPolicy] = {}
    purposes = {
        "login_webauthn": "account.login",
        "authenticate_webauthn": "account.authenticate",
        "reauthenticate_webauthn": "account.reauthenticate",
    }
    for client in ("app", "browser"):
        namespace = f"headless:{client}:mfa"
        for name, purpose in purposes.items():
            policies[f"{namespace}:{name}"] = _CeremonyPolicy(
                method="POST",
                expected_type=WEBAUTHN_GET,
                surface=ACCOUNT_SURFACE,
                nested_credential=True,
                purpose=purpose,
            )
        policies[f"{namespace}:manage_webauthn"] = _CeremonyPolicy(
            method="POST",
            expected_type=WEBAUTHN_CREATE,
            surface=ACCOUNT_SURFACE,
            nested_credential=True,
            purpose="account.register",
        )
        policies[f"{namespace}:signup_webauthn"] = _CeremonyPolicy(
            method="PUT",
            expected_type=WEBAUTHN_CREATE,
            surface=ACCOUNT_SURFACE,
            nested_credential=True,
            purpose="account.signup",
        )

    policies["admin:admin_mfa_webauthn_complete"] = _CeremonyPolicy(
        method="POST",
        expected_type=WEBAUTHN_GET,
        surface=ADMIN_SURFACE,
        nested_credential=False,
        purpose="admin.authenticate",
    )
    return MappingProxyType(policies)


def _build_options_policies() -> MappingProxyType:
    policies = {
        route: _CeremonyPolicy(
            method="GET",
            expected_type=policy.expected_type,
            surface=policy.surface,
            nested_credential=policy.nested_credential,
            purpose=policy.purpose,
        )
        for route, policy in WEBAUTHN_COMPLETION_POLICIES.items()
        if policy.surface == ACCOUNT_SURFACE
    }
    policies["admin:admin_mfa_webauthn_options"] = _CeremonyPolicy(
        method="GET",
        expected_type=WEBAUTHN_GET,
        surface=ADMIN_SURFACE,
        nested_credential=False,
        purpose="admin.authenticate",
    )
    return MappingProxyType(policies)


WEBAUTHN_COMPLETION_POLICIES = _build_completion_policies()
WEBAUTHN_OPTIONS_POLICIES = _build_options_policies()
_WEBAUTHN_ROUTES = frozenset(
    {*WEBAUTHN_COMPLETION_POLICIES, *WEBAUTHN_OPTIONS_POLICIES}
)


def _route_name(request: HttpRequest) -> str:
    match = getattr(request, "resolver_match", None)
    return getattr(match, "view_name", "") or ""


def _allowed_origins(surface: str) -> tuple[str, ...]:
    setting_name = (
        "WEBAUTHN_ADMIN_ORIGINS"
        if surface == ADMIN_SURFACE
        else "WEBAUTHN_ACCOUNT_ORIGINS"
    )
    origins = getattr(settings, setting_name, ())
    if isinstance(origins, (str, bytes)):
        return ()
    try:
        return tuple(origins)
    except TypeError:
        return ()


def _parse_request_payload(
    request: HttpRequest,
    policy: _CeremonyPolicy,
) -> object:
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (
        json.JSONDecodeError,
        RawPostDataException,
        RequestDataTooBig,
        UnicodeDecodeError,
    ) as exc:
        raise WebAuthnClientDataError("invalid_request_json") from exc
    if policy.nested_credential:
        if not isinstance(payload, dict) or "credential" not in payload:
            raise WebAuthnClientDataError("invalid_credential_shape")
        return payload["credential"]
    return payload


def _response_payload(response: HttpResponse) -> dict | None:
    try:
        payload = json.loads(response.content.decode("utf-8"))
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _response_session_token(response: HttpResponse) -> str | None:
    header_token = response.headers.get("X-Session-Token")
    if isinstance(header_token, str) and header_token:
        return header_token
    payload = _response_payload(response)
    meta = payload.get("meta") if payload else None
    token = meta.get("session_token") if isinstance(meta, dict) else None
    return token if isinstance(token, str) and token else None


def _boundary_session(
    request: HttpRequest,
    route: str,
    *,
    response: HttpResponse | None = None,
) -> _BoundarySession | None:
    if not route.startswith("headless:app:"):
        session = getattr(request, "session", None)
        if isinstance(session, SessionBase):
            return _BoundarySession(store=session, external=False)
        return None

    token = request.headers.get("X-Session-Token")
    if not token and response is not None:
        token = _response_session_token(response)
    if not token:
        return None
    try:
        session = headless_app_settings.TOKEN_STRATEGY.lookup_session(token)
    except Exception:
        # A strategy/backend outage must never turn challenge binding into a
        # fail-open path. The token itself is intentionally not logged.
        return None
    if not isinstance(session, SessionBase):
        return None
    return _BoundarySession(store=session, external=True)


def _persist_session(boundary: _BoundarySession) -> None:
    try:
        boundary.store.save()
    except Exception as exc:
        raise _ChallengeBoundaryError("challenge_session_save_failed") from exc


def _clear_challenge(boundary: _BoundarySession) -> None:
    if WEBAUTHN_CHALLENGE_SESSION_KEY not in boundary.store:
        return
    boundary.store.pop(WEBAUTHN_CHALLENGE_SESSION_KEY, None)
    _persist_session(boundary)


def _digest_binding(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _session_binding_digest(
    boundary: _BoundarySession,
    *,
    create: bool,
) -> str | None:
    binding = boundary.store.get(WEBAUTHN_SESSION_BINDING_KEY)
    if not isinstance(binding, str) or len(binding) < 32:
        if not create:
            return None
        binding = secrets.token_urlsafe(32)
        boundary.store[WEBAUTHN_SESSION_BINDING_KEY] = binding
    return _digest_binding(binding)


def _subject_binding(
    boundary: _BoundarySession,
    policy: _CeremonyPolicy,
) -> str | None:
    session = boundary.store
    if policy.surface == ADMIN_SURFACE:
        pending = session.get(SESSION_KEY_ADMIN_MFA_PENDING)
        if not isinstance(pending, dict) or pending.get("version") != 1:
            return None
        user_pk = pending.get("user_pk")
        flow_id = pending.get("flow_id")
        if not isinstance(user_pk, str) or not user_pk:
            return None
        if not isinstance(flow_id, str) or len(flow_id) < 16:
            return None
        return f"admin:{user_pk}:{flow_id}"

    if policy.purpose == "account.login":
        # A discoverable credential identifies its user only at completion.
        # Purpose + the random session binding still isolate this ceremony.
        return None

    if policy.purpose in {"account.authenticate", "account.signup"}:
        pending = session.get(_ACCOUNT_LOGIN_SESSION_KEY)
        if not isinstance(pending, dict):
            return None
        user_pk = pending.get("user_pk")
        initiated_at = pending.get("initiated_at")
        if not isinstance(user_pk, str) or not user_pk:
            return None
        if isinstance(initiated_at, bool) or not isinstance(
            initiated_at, (int, float)
        ):
            return None
        initiated_at = float(initiated_at)
        if not math.isfinite(initiated_at):
            return None
        return f"pending:{user_pk}:{initiated_at!r}"

    user_pk = session.get(SESSION_KEY)
    if user_pk is None:
        return None
    user_pk = str(user_pk)
    if not user_pk:
        return None
    return f"authenticated:{user_pk}"


def _subject_binding_digest(
    boundary: _BoundarySession,
    policy: _CeremonyPolicy,
) -> str | None:
    binding = _subject_binding(boundary, policy)
    return _digest_binding(binding) if binding is not None else None


def _options_payload_and_public_key(
    response: HttpResponse,
    policy: _CeremonyPolicy,
) -> tuple[dict, dict]:
    payload = _response_payload(response)
    if payload is None:
        raise _ChallengeBoundaryError("options_response_invalid")
    if policy.surface == ADMIN_SURFACE:
        options = payload
    else:
        data = payload.get("data")
        if not isinstance(data, dict):
            raise _ChallengeBoundaryError("options_response_invalid")
        option_key = (
            "creation_options"
            if policy.expected_type == WEBAUTHN_CREATE
            else "request_options"
        )
        options = data.get(option_key)
    if not isinstance(options, dict):
        raise _ChallengeBoundaryError("options_response_invalid")
    public_key = options.get("publicKey")
    if not isinstance(public_key, dict):
        raise _ChallengeBoundaryError("options_response_invalid")
    return payload, public_key


def _extract_options_challenge(
    response: HttpResponse,
    policy: _CeremonyPolicy,
) -> object:
    _, public_key = _options_payload_and_public_key(response, policy)
    return public_key.get("challenge")


def _require_passwordless_user_verification(
    boundary: _BoundarySession,
    policy: _CeremonyPolicy,
    response: HttpResponse,
) -> None:
    if policy.purpose != "account.login":
        return
    payload, public_key = _options_payload_and_public_key(response, policy)
    try:
        require_webauthn_user_verification(boundary.store, public_key)
    except WebAuthnStateError as exc:
        raise _ChallengeBoundaryError(
            "user_verification_state_invalid"
        ) from exc

    # JsonResponse has already rendered its body. Re-serialize the same
    # envelope after strengthening the browser-visible request options;
    # CommonMiddleware runs outside this middleware and calculates the final
    # Content-Length afterwards.
    response.content = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode(response.charset)


def _challenge_ttl() -> int:
    value = getattr(settings, "WEBAUTHN_CHALLENGE_TTL_SECONDS", None)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise _ChallengeBoundaryError("challenge_ttl_invalid")
    return value


def _is_sha256_digest(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256_DIGEST_RE.fullmatch(value))


def _store_challenge(
    boundary: _BoundarySession,
    policy: _CeremonyPolicy,
    response: HttpResponse,
) -> None:
    _challenge_ttl()
    challenge = _extract_options_challenge(response, policy)
    session_digest = _session_binding_digest(boundary, create=True)
    if session_digest is None:  # pragma: no cover - create=True guarantees it
        raise _ChallengeBoundaryError("session_binding_missing")
    subject_digest = _subject_binding_digest(boundary, policy)
    if policy.purpose != "account.login" and subject_digest is None:
        raise _ChallengeBoundaryError("subject_binding_missing")

    try:
        challenge_digest = webauthn_challenge_digest(challenge)
    except WebAuthnClientDataError as exc:
        raise _ChallengeBoundaryError("options_challenge_invalid") from exc

    boundary.store[WEBAUTHN_CHALLENGE_SESSION_KEY] = {
        "version": _METADATA_VERSION,
        "purpose": policy.purpose,
        "issued_at": time.time(),
        "challenge_digest": challenge_digest,
        "session_binding_digest": session_digest,
        "subject_binding_digest": subject_digest,
        "nonce": secrets.token_urlsafe(32),
    }
    _persist_session(boundary)


def _consume_challenge(
    boundary: _BoundarySession,
    policy: _CeremonyPolicy,
) -> dict:
    metadata = boundary.store.pop(WEBAUTHN_CHALLENGE_SESSION_KEY, None)
    # Persist the pop before parsing attacker-controlled completion data. A
    # shared-cache nonce claim below closes the concurrent stale-session race.
    _persist_session(boundary)
    if not isinstance(metadata, dict):
        raise _ChallengeBoundaryError("challenge_metadata_missing")
    if metadata.get("version") != _METADATA_VERSION:
        raise _ChallengeBoundaryError("challenge_metadata_invalid")

    issued_at = metadata.get("issued_at")
    if isinstance(issued_at, bool) or not isinstance(issued_at, (int, float)):
        raise _ChallengeBoundaryError("challenge_metadata_invalid")
    issued_at = float(issued_at)
    if not math.isfinite(issued_at):
        raise _ChallengeBoundaryError("challenge_metadata_invalid")
    ttl = _challenge_ttl()
    age = time.time() - issued_at
    if age < 0 or age > ttl:
        raise _ChallengeBoundaryError("challenge_expired")

    expected_session_digest = _session_binding_digest(boundary, create=False)
    session_digest = metadata.get("session_binding_digest")
    if (
        expected_session_digest is None
        or not _is_sha256_digest(session_digest)
        or not secrets.compare_digest(session_digest, expected_session_digest)
    ):
        raise _ChallengeBoundaryError("session_binding_mismatch")

    nonce = metadata.get("nonce")
    if not isinstance(nonce, str) or not 32 <= len(nonce) <= 256:
        raise _ChallengeBoundaryError("challenge_metadata_invalid")
    claim_key = (
        _CLAIM_CACHE_PREFIX + hashlib.sha256(nonce.encode("utf-8")).hexdigest()
    )
    try:
        replay_cache = caches[settings.WEBAUTHN_REPLAY_CACHE_ALIAS]
        claimed = replay_cache.add(claim_key, True, timeout=ttl)
    except Exception as exc:
        raise _ChallengeBoundaryError("challenge_claim_failed") from exc
    if not claimed:
        raise _ChallengeBoundaryError("challenge_replayed")

    if metadata.get("purpose") != policy.purpose:
        raise _ChallengeBoundaryError("challenge_purpose_mismatch")
    expected_subject_digest = _subject_binding_digest(boundary, policy)
    subject_digest = metadata.get("subject_binding_digest")
    if policy.purpose == "account.login":
        if subject_digest is not None:
            raise _ChallengeBoundaryError("subject_binding_mismatch")
    elif (
        expected_subject_digest is None
        or not _is_sha256_digest(subject_digest)
        or not secrets.compare_digest(subject_digest, expected_subject_digest)
    ):
        raise _ChallengeBoundaryError("subject_binding_mismatch")

    challenge_digest = metadata.get("challenge_digest")
    if not _is_sha256_digest(challenge_digest):
        raise _ChallengeBoundaryError("challenge_metadata_invalid")
    return metadata


def _generic_rejection(status: int = 400) -> JsonResponse:
    response = JsonResponse({"error": _GENERIC_ERROR}, status=status)
    if status == 429:
        response["Retry-After"] = "60"
    return response


def _register_admin_boundary_failure(
    request: HttpRequest,
) -> JsonResponse | None:
    pending = get_pending_admin_login(request)
    if pending is None:
        return None
    try:
        register_admin_webauthn_boundary_failure(request, pending)
    except AdminMFARateLimitError:
        logger.warning(
            "Admin WebAuthn boundary rate limited route=%s reason=%s",
            _route_name(request),
            "completion_rate_limited",
            extra={
                "event": "admin.mfa.rate_limited",
                "method": "webauthn",
                "reason_code": "completion_rate_limited",
                "request_id": getattr(request, "request_id", None),
                "route": _route_name(request),
            },
        )
        return _generic_rejection(status=429)
    except Exception:
        logger.error(
            "Admin WebAuthn boundary accounting failed route=%s reason=%s",
            _route_name(request),
            "boundary_accounting_failed",
            extra={
                "event": "admin.mfa.boundary_accounting_failed",
                "method": "webauthn",
                "reason_code": "boundary_accounting_failed",
                "request_id": getattr(request, "request_id", None),
                "route": _route_name(request),
            },
        )
        return _generic_rejection()
    return None


def _log_rejection(
    request: HttpRequest,
    route: str,
    reason_code: str,
    *,
    event: str,
) -> None:
    try:
        request_host = request.get_host().split(":", 1)[0].lower()
    except DisallowedHost:
        request_host = "<invalid>"
    logger.warning(
        "WebAuthn ceremony rejected route=%s reason=%s",
        route,
        reason_code,
        extra={
            "event": event,
            "reason_code": reason_code,
            "route": route,
            "request_id": getattr(request, "request_id", None),
            "request_host": request_host,
            "request_method": request.method,
        },
    )


class WebAuthnOriginValidationMiddleware:
    """Enforce exact origin and one-use challenge bindings before FIDO2."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        route = _route_name(request)
        policy = WEBAUTHN_OPTIONS_POLICIES.get(route)
        if (
            policy is not None
            and request.method == policy.method
            and 200 <= response.status_code < 300
        ):
            try:
                boundary = _boundary_session(request, route, response=response)
                if boundary is None:
                    raise _ChallengeBoundaryError("challenge_session_missing")
                _require_passwordless_user_verification(
                    boundary,
                    policy,
                    response,
                )
                _store_challenge(boundary, policy, response)
            except _ChallengeBoundaryError as exc:
                _log_rejection(
                    request,
                    route,
                    exc.reason_code,
                    event="webauthn.challenge_rejected",
                )
                response = _generic_rejection()

        if route in _WEBAUTHN_ROUTES:
            patch_cache_control(
                response,
                private=True,
                no_cache=True,
                no_store=True,
                must_revalidate=True,
                max_age=0,
            )
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        route = _route_name(request)
        options_policy = WEBAUTHN_OPTIONS_POLICIES.get(route)
        if (
            options_policy is not None
            and request.method == options_policy.method
        ):
            boundary = _boundary_session(request, route)
            if boundary is not None:
                try:
                    _clear_challenge(boundary)
                except _ChallengeBoundaryError as exc:
                    _log_rejection(
                        request,
                        route,
                        exc.reason_code,
                        event="webauthn.challenge_rejected",
                    )
                    return _generic_rejection()
            return None

        policy = WEBAUTHN_COMPLETION_POLICIES.get(route)
        if policy is None or request.method != policy.method:
            return None

        reason_code = ""
        event = "webauthn.challenge_rejected"
        try:
            boundary = _boundary_session(request, route)
            if boundary is None:
                raise _ChallengeBoundaryError("challenge_session_missing")
            metadata = _consume_challenge(boundary, policy)
            credential = _parse_request_payload(request, policy)
            client_data = validate_webauthn_client_data(
                credential,
                expected_type=policy.expected_type,
                allowed_origins=_allowed_origins(policy.surface),
            )
            signed_challenge_digest = hashlib.sha256(
                client_data.challenge
            ).hexdigest()
            if not secrets.compare_digest(
                signed_challenge_digest,
                metadata["challenge_digest"],
            ):
                raise _ChallengeBoundaryError("challenge_mismatch")
        except WebAuthnClientDataError as exc:
            reason_code = exc.reason_code
            event = (
                "webauthn.origin_rejected"
                if reason_code in _ORIGIN_REJECTION_REASONS
                else "webauthn.challenge_rejected"
            )
        except _ChallengeBoundaryError as exc:
            reason_code = exc.reason_code

        if not reason_code:
            return None

        _log_rejection(request, route, reason_code, event=event)
        if policy.surface == ADMIN_SURFACE:
            rate_response = _register_admin_boundary_failure(request)
            if rate_response is not None:
                return rate_response
        return _generic_rejection()


__all__ = [
    "WEBAUTHN_COMPLETION_POLICIES",
    "WEBAUTHN_OPTIONS_POLICIES",
    "WebAuthnOriginValidationMiddleware",
]
