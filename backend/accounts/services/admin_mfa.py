from __future__ import annotations

import hashlib
import math
import re
import secrets
import time
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from accounts.adapters import StrictAccountAdapter
from accounts.webauthn import (
    WEBAUTHN_CHALLENGE_SESSION_KEY,
    WEBAUTHN_GET,
    WEBAUTHN_SESSION_BINDING_KEY,
    WebAuthnClientDataError,
    validate_webauthn_client_data,
)
from allauth.core import ratelimit as allauth_ratelimit
from allauth.mfa.base.forms import AuthenticateForm
from allauth.mfa.models import Authenticator
from allauth.mfa.webauthn.forms import AuthenticateWebAuthnForm
from allauth.mfa.webauthn.internal import auth as allauth_webauthn
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.core.cache import caches
from django.db import transaction
from django.http import HttpRequest
from django.utils.http import url_has_allowed_host_and_scheme
from django_ratelimit.core import is_ratelimited
from fido2.webauthn import UserVerificationRequirement

SESSION_KEY_ADMIN_MFA_PENDING = "_admin_mfa_pending"
SESSION_KEY_ADMIN_MFA_ASSURANCE = "_admin_mfa_assurance"

PRIMARY_ADMIN_MFA_TYPES = (
    Authenticator.Type.TOTP,
    Authenticator.Type.WEBAUTHN,
)
ADMIN_MFA_METHODS = frozenset({"totp", "recovery_code", "webauthn"})

RATE_GROUP_CODE = "admin.mfa.code"
RATE_GROUP_WEBAUTHN_COMPLETION = "admin.mfa.webauthn.completion"
RATE_GROUP_WEBAUTHN_OPTIONS = "admin.mfa.webauthn.options"
_RATE_EPOCH_CACHE_PREFIX = "admin-mfa:rate-epoch:"
_RATE_EPOCH_BYTES = 24
_RATE_WINDOW_RE = re.compile(r"^\d+/(\d*)([smhd])?$")
_RATE_WINDOW_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_RATE_EPOCH_EXPIRY_FUDGE_SECONDS = 60

AdminMFAMethod = Literal["totp", "recovery_code", "webauthn"]


class AdminMFAError(Exception):
    """Base class for safe, expected admin MFA failures."""

    def __init__(self, reason_code: str):
        self.reason_code = reason_code
        super().__init__(reason_code)


class AdminMFAVerificationError(AdminMFAError):
    """The supplied factor or pending flow was invalid."""


class AdminMFARateLimitError(AdminMFAError):
    """The admin MFA flow exceeded its dedicated rate limit."""


@dataclass(frozen=True)
class PendingAdminLogin:
    user: object
    started_at: float
    next_url: str
    flow_id: str


@dataclass(frozen=True)
class AdminMFAVerification:
    authenticator: Authenticator
    method: AdminMFAMethod


def admin_user_has_primary_mfa(user: object | None) -> bool:
    """Return whether ``user`` has a TOTP or WebAuthn authenticator."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    user_pk = getattr(user, "pk", None)
    if user_pk is None:
        return False
    return Authenticator.objects.filter(
        user_id=user_pk,
        type__in=PRIMARY_ADMIN_MFA_TYPES,
    ).exists()


def admin_user_has_webauthn(user: object | None) -> bool:
    if not user:
        return False
    user_pk = getattr(user, "pk", None)
    if user_pk is None:
        return False
    return Authenticator.objects.filter(
        user_id=user_pk,
        type=Authenticator.Type.WEBAUTHN,
    ).exists()


def _positive_setting(name: str, default: int) -> int:
    value = getattr(settings, name, default)
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _now() -> float:
    return time.time()


def _valid_timestamp(value: object, *, ttl: int) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    timestamp = float(value)
    if not math.isfinite(timestamp):
        return False
    age = _now() - timestamp
    return 0 <= age <= ttl


def safe_admin_next(request: HttpRequest, candidate: object) -> str:
    """Normalize a redirect target to a local, protected admin path."""
    fallback = "/admin/"
    if (
        not isinstance(candidate, str)
        or not candidate
        or len(candidate) > 2048
    ):
        return fallback
    if "\\" in candidate or any(
        ord(character) < 32 or ord(character) == 127 for character in candidate
    ):
        return fallback
    if not url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return fallback

    parsed = urlsplit(candidate)
    path = parsed.path
    # Browsers and proxies may normalize dot segments after Django has made
    # its redirect decision. Reject encoded paths outright so repeated
    # percent-decoding cannot turn an apparently protected path into `..`.
    if "%" in path or any(
        segment in {".", ".."} for segment in path.split("/")
    ):
        return fallback
    if not path.startswith("/admin/"):
        return fallback
    if path.startswith(
        (
            "/admin/login/",
            "/admin/logout/",
            "/admin/mfa-verify/",
        )
    ):
        return fallback
    return urlunsplit(("", "", path, parsed.query, ""))


def clear_pending_admin_login(request: HttpRequest) -> None:
    request.session.pop(SESSION_KEY_ADMIN_MFA_PENDING, None)
    request.session.pop(allauth_webauthn.STATE_SESSION_KEY, None)
    request.session.pop(WEBAUTHN_CHALLENGE_SESSION_KEY, None)
    request.session.pop(WEBAUTHN_SESSION_BINDING_KEY, None)


def clear_admin_mfa_state(request: HttpRequest) -> None:
    clear_pending_admin_login(request)
    request.session.pop(SESSION_KEY_ADMIN_MFA_ASSURANCE, None)


def abort_pending_admin_login(
    request: HttpRequest,
    pending: PendingAdminLogin,
) -> None:
    """End a blocked flow and reset allauth's matching MFA counter."""
    allauth_ratelimit.clear(
        request,
        action="login_failed",
        key=f"mfa-auth-user-{pending.user.pk}",
    )
    clear_admin_mfa_state(request)


def start_pending_admin_login(
    request: HttpRequest,
    user,
    *,
    next_url: object,
) -> PendingAdminLogin:
    """Start a password-authenticated, session-bound MFA flow."""
    if not (
        getattr(user, "is_active", False)
        and getattr(user, "is_staff", False)
        and admin_user_has_primary_mfa(user)
    ):
        clear_admin_mfa_state(request)
        raise AdminMFAVerificationError("admin_mfa_required")
    clear_admin_mfa_state(request)
    request.session.cycle_key()
    started_at = _now()
    state = {
        "version": 1,
        "user_pk": str(user.pk),
        "started_at": started_at,
        "next": safe_admin_next(request, next_url),
        "flow_id": secrets.token_urlsafe(24),
    }
    request.session[SESSION_KEY_ADMIN_MFA_PENDING] = state
    return PendingAdminLogin(
        user=user,
        started_at=started_at,
        next_url=state["next"],
        flow_id=state["flow_id"],
    )


def get_pending_admin_login(
    request: HttpRequest,
) -> PendingAdminLogin | None:
    state = request.session.get(SESSION_KEY_ADMIN_MFA_PENDING)
    ttl = _positive_setting("ADMIN_MFA_PENDING_TTL_SECONDS", 300)
    if not isinstance(state, dict) or state.get("version") != 1:
        clear_pending_admin_login(request)
        return None

    user_pk = state.get("user_pk")
    started_at = state.get("started_at")
    flow_id = state.get("flow_id")
    if (
        not isinstance(user_pk, str)
        or not user_pk
        or not isinstance(flow_id, str)
        or len(flow_id) < 16
        or not _valid_timestamp(started_at, ttl=ttl)
    ):
        clear_pending_admin_login(request)
        return None

    user_model = get_user_model()
    user = user_model._default_manager.filter(
        pk=user_pk,
        is_staff=True,
        is_active=True,
    ).first()
    if user is None or not admin_user_has_primary_mfa(user):
        clear_pending_admin_login(request)
        return None

    next_url = safe_admin_next(request, state.get("next"))
    return PendingAdminLogin(
        user=user,
        started_at=float(started_at),
        next_url=next_url,
        flow_id=flow_id,
    )


def is_admin_mfa_verified(request: HttpRequest) -> bool:
    user = getattr(request, "user", None)
    session = getattr(request, "session", None)
    if session is None:
        return False
    if not (
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and getattr(user, "is_staff", False)
    ):
        session.pop(SESSION_KEY_ADMIN_MFA_ASSURANCE, None)
        return False

    state = session.get(SESSION_KEY_ADMIN_MFA_ASSURANCE)
    ttl = _positive_setting("ADMIN_MFA_ASSURANCE_TTL_SECONDS", 28800)
    if not isinstance(state, dict) or state.get("version") != 1:
        session.pop(SESSION_KEY_ADMIN_MFA_ASSURANCE, None)
        return False
    assured_user_pk = state.get("user_pk")
    if not isinstance(assured_user_pk, str) or assured_user_pk != str(user.pk):
        session.pop(SESSION_KEY_ADMIN_MFA_ASSURANCE, None)
        return False
    if state.get("method") not in ADMIN_MFA_METHODS:
        session.pop(SESSION_KEY_ADMIN_MFA_ASSURANCE, None)
        return False
    if not _valid_timestamp(state.get("verified_at"), ttl=ttl):
        session.pop(SESSION_KEY_ADMIN_MFA_ASSURANCE, None)
        return False
    return True


def admin_request_has_mfa_assurance(request: HttpRequest) -> bool:
    user = getattr(request, "user", None)
    if not (
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and getattr(user, "is_staff", False)
    ):
        request.session.pop(SESSION_KEY_ADMIN_MFA_ASSURANCE, None)
        return False
    if not is_admin_mfa_verified(request):
        return False
    if not admin_user_has_primary_mfa(user):
        request.session.pop(SESSION_KEY_ADMIN_MFA_ASSURANCE, None)
        return False
    return True


def _rate_identity(
    request: HttpRequest,
    pending: PendingAdminLogin,
) -> str:
    client_ip = StrictAccountAdapter().get_client_ip(request)
    return f"user:{pending.user.pk}|ip:{client_ip}"


def _rate_epoch_cache_key(identity: str) -> str:
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return f"{_RATE_EPOCH_CACHE_PREFIX}{digest}"


def _new_rate_epoch() -> str:
    return secrets.token_urlsafe(_RATE_EPOCH_BYTES)


def _rate_window_seconds(rate: str) -> int:
    match = _RATE_WINDOW_RE.fullmatch(rate)
    if match is None:
        raise AdminMFARateLimitError("rate_limit_configuration_invalid")
    multiplier = int(match.group(1) or "1")
    unit = match.group(2) or "s"
    if multiplier <= 0:
        raise AdminMFARateLimitError("rate_limit_configuration_invalid")
    return multiplier * _RATE_WINDOW_SECONDS[unit]


def _rate_epoch_timeout() -> int:
    # Refreshing the epoch for at least the longest project-owned rate window
    # ensures a restarted password flow cannot detach a still-live counter.
    # The finite timeout also bounds user+trusted-IP cardinality.
    longest_window = max(
        _rate_window_seconds(_verification_rate()),
        _rate_window_seconds(_options_rate()),
    )
    return longest_window + _RATE_EPOCH_EXPIRY_FUDGE_SECONDS


def _rate_limit_cache():
    return caches[settings.RATELIMIT_USE_CACHE]


def _get_rate_epoch(identity: str) -> str:
    cache_key = _rate_epoch_cache_key(identity)
    candidate = _new_rate_epoch()
    timeout = _rate_epoch_timeout()
    try:
        backend = _rate_limit_cache()
        added = backend.add(cache_key, candidate, timeout=timeout)
        epoch = backend.get(cache_key)
        if not added and epoch is not None:
            if not backend.touch(cache_key, timeout=timeout):
                raise AdminMFARateLimitError("rate_limit_backend_unavailable")
    except Exception as exc:
        if isinstance(exc, AdminMFARateLimitError):
            raise
        raise AdminMFARateLimitError("rate_limit_backend_unavailable") from exc
    if not isinstance(epoch, str) or len(epoch) < _RATE_EPOCH_BYTES:
        raise AdminMFARateLimitError("rate_limit_backend_unavailable")
    return epoch


def _rotate_rate_epoch(
    request: HttpRequest,
    pending: PendingAdminLogin,
) -> None:
    identity = _rate_identity(request, pending)
    cache_key = _rate_epoch_cache_key(identity)
    epoch = _new_rate_epoch()
    timeout = _rate_epoch_timeout()
    try:
        backend = _rate_limit_cache()
        backend.set(cache_key, epoch, timeout=timeout)
        stored_epoch = backend.get(cache_key)
    except Exception as exc:
        if isinstance(exc, AdminMFARateLimitError):
            raise
        raise AdminMFARateLimitError("rate_limit_backend_unavailable") from exc
    if not isinstance(stored_epoch, str) or not secrets.compare_digest(
        stored_epoch,
        epoch,
    ):
        raise AdminMFARateLimitError("rate_limit_backend_unavailable")


def _rate_key(
    request: HttpRequest,
    pending: PendingAdminLogin,
) -> str:
    identity = _rate_identity(request, pending)
    epoch = _get_rate_epoch(identity)
    return f"{identity}|epoch:{epoch}"


def _is_rate_limited(
    request: HttpRequest,
    pending: PendingAdminLogin,
    *,
    group: str,
    rate: str,
    increment: bool,
) -> bool:
    value = _rate_key(request, pending)
    try:
        return is_ratelimited(
            request,
            group=group,
            key=lambda _group, _request: value,
            rate=rate,
            increment=increment,
        )
    except Exception as exc:
        raise AdminMFARateLimitError("rate_limit_backend_unavailable") from exc


def _verification_rate() -> str:
    return str(getattr(settings, "ADMIN_MFA_COMPLETION_RATE", "5/m"))


def _options_rate() -> str:
    return str(getattr(settings, "ADMIN_MFA_OPTIONS_RATE", "20/m"))


def _precheck_verification_rate(
    request: HttpRequest,
    pending: PendingAdminLogin,
    *,
    group: str,
) -> None:
    if _is_rate_limited(
        request,
        pending,
        group=group,
        rate=_verification_rate(),
        increment=False,
    ):
        raise AdminMFARateLimitError("rate_limited")


def _register_failed_verification(
    request: HttpRequest,
    pending: PendingAdminLogin,
    *,
    group: str,
) -> None:
    if _is_rate_limited(
        request,
        pending,
        group=group,
        rate=_verification_rate(),
        increment=True,
    ):
        raise AdminMFARateLimitError("rate_limited")


def register_failed_code_verification(
    request: HttpRequest,
    pending: PendingAdminLogin,
) -> None:
    _register_failed_verification(
        request,
        pending,
        group=RATE_GROUP_CODE,
    )


def register_failed_webauthn_verification(
    request: HttpRequest,
    pending: PendingAdminLogin,
) -> None:
    _register_failed_verification(
        request,
        pending,
        group=RATE_GROUP_WEBAUTHN_COMPLETION,
    )


def register_admin_webauthn_boundary_failure(
    request: HttpRequest,
    pending: PendingAdminLogin,
) -> None:
    """Count an origin-boundary rejection in the WebAuthn completion quota."""
    try:
        register_failed_webauthn_verification(request, pending)
    except AdminMFARateLimitError:
        abort_pending_admin_login(request, pending)
        raise


def _form_is_rate_limited(form, field: str) -> bool:
    return any(
        error.code == "too_many_login_attempts"
        for error in form.errors.as_data().get(field, ())
    )


def _method_for(authenticator: Authenticator) -> AdminMFAMethod:
    if authenticator.type == Authenticator.Type.TOTP:
        return "totp"
    if authenticator.type == Authenticator.Type.RECOVERY_CODES:
        return "recovery_code"
    if authenticator.type == Authenticator.Type.WEBAUTHN:
        return "webauthn"
    raise AdminMFAVerificationError("unsupported_authenticator")


def verify_admin_code(
    request: HttpRequest,
    pending: PendingAdminLogin,
    code: str,
) -> AdminMFAVerification:
    _precheck_verification_rate(
        request,
        pending,
        group=RATE_GROUP_CODE,
    )

    with transaction.atomic():
        # RecoveryCodes.validate_code() updates a JSON bitmask. Lock both
        # code-based rows so concurrent submissions cannot consume one code
        # twice or lose an update.
        list(
            Authenticator.objects.select_for_update().filter(
                user_id=pending.user.pk,
                type__in=(
                    Authenticator.Type.TOTP,
                    Authenticator.Type.RECOVERY_CODES,
                ),
            )
        )
        form = AuthenticateForm(user=pending.user, data={"code": code})
        is_valid = form.is_valid()
        allauth_rate_limited = _form_is_rate_limited(form, "code")
        if is_valid:
            form.save()
            authenticator = form.authenticator
            return AdminMFAVerification(
                authenticator=authenticator,
                method=_method_for(authenticator),
            )

    # Do not raise from the atomic block. Both allauth's login_failed counter
    # and the DatabaseCache-backed TOTP replay marker write through the same
    # database connection; an exception escaping `atomic()` would silently
    # roll those security writes back in production.
    register_failed_code_verification(request, pending)
    if allauth_rate_limited:
        raise AdminMFARateLimitError("allauth_rate_limited")
    reason = "missing_code" if not code else "incorrect_code"
    raise AdminMFAVerificationError(reason)


def begin_admin_webauthn(
    request: HttpRequest,
    pending: PendingAdminLogin,
) -> dict:
    if not admin_user_has_webauthn(pending.user):
        raise AdminMFAVerificationError("webauthn_not_enrolled")
    if _is_rate_limited(
        request,
        pending,
        group=RATE_GROUP_WEBAUTHN_OPTIONS,
        rate=_options_rate(),
        increment=True,
    ):
        raise AdminMFARateLimitError("rate_limited")

    # This is the only project-owned facade around allauth's private WebAuthn
    # state. AccountMiddleware already provides allauth.core.context.request.
    options = allauth_webauthn.begin_authentication(user=pending.user)
    state = request.session.get(allauth_webauthn.STATE_SESSION_KEY)
    public_key = (
        options.get("publicKey") if isinstance(options, dict) else None
    )
    if not isinstance(state, dict) or not isinstance(public_key, dict):
        clear_pending_admin_login(request)
        raise AdminMFAVerificationError("webauthn_state_invalid")

    # Mutate both the browser request and server-side state. FIDO2 checks the
    # state value during authenticate_complete(), so merely changing the JSON
    # option would not enforce user verification.
    state["user_verification"] = UserVerificationRequirement.REQUIRED
    request.session[allauth_webauthn.STATE_SESSION_KEY] = state
    public_key["userVerification"] = UserVerificationRequirement.REQUIRED.value
    return options


def verify_admin_webauthn(
    request: HttpRequest,
    pending: PendingAdminLogin,
    credential: dict,
) -> AdminMFAVerification:
    _precheck_verification_rate(
        request,
        pending,
        group=RATE_GROUP_WEBAUTHN_COMPLETION,
    )

    allowed_origins = getattr(settings, "WEBAUTHN_ADMIN_ORIGINS", ())
    if not allowed_origins:
        register_failed_webauthn_verification(request, pending)
        raise AdminMFAVerificationError("origin_policy_missing")
    try:
        validate_webauthn_client_data(
            credential,
            expected_type=WEBAUTHN_GET,
            allowed_origins=allowed_origins,
        )
    except WebAuthnClientDataError as exc:
        register_failed_webauthn_verification(request, pending)
        raise AdminMFAVerificationError(exc.reason_code) from exc

    form = AuthenticateWebAuthnForm(
        user=pending.user,
        data={"credential": credential},
    )
    if not form.is_valid():
        if _form_is_rate_limited(form, "credential"):
            raise AdminMFARateLimitError("allauth_rate_limited")
        register_failed_webauthn_verification(request, pending)
        raise AdminMFAVerificationError("incorrect_webauthn")

    form.save()
    authenticator = form.cleaned_data["credential"]
    return AdminMFAVerification(
        authenticator=authenticator,
        method=_method_for(authenticator),
    )


def complete_admin_login(
    request: HttpRequest,
    pending: PendingAdminLogin,
    verification: AdminMFAVerification,
) -> str:
    user = pending.user
    user.refresh_from_db(fields=("is_active", "is_staff"))
    if not user.is_active or not user.is_staff:
        clear_admin_mfa_state(request)
        raise AdminMFAVerificationError("admin_role_changed")
    if verification.authenticator.user_id != user.pk:
        clear_admin_mfa_state(request)
        raise AdminMFAVerificationError("authenticator_user_mismatch")
    if not Authenticator.objects.filter(
        pk=verification.authenticator.pk,
        user_id=user.pk,
        type=verification.authenticator.type,
    ).exists():
        clear_admin_mfa_state(request)
        raise AdminMFAVerificationError("authenticator_removed")
    if not admin_user_has_primary_mfa(user):
        clear_admin_mfa_state(request)
        raise AdminMFAVerificationError("primary_mfa_removed")

    next_url = safe_admin_next(request, pending.next_url)
    # Failed or restarted password flows keep the same user+trusted-IP epoch,
    # so they cannot mint fresh MFA attempts. Only a fully verified factor
    # rotates all project-owned rate groups for the next legitimate login.
    _rotate_rate_epoch(request, pending)
    clear_admin_mfa_state(request)
    previous_session_key = request.session.session_key
    auth_login(
        request,
        user,
        backend="django.contrib.auth.backends.ModelBackend",
    )
    if request.session.session_key == previous_session_key:
        request.session.cycle_key()
    request.session[SESSION_KEY_ADMIN_MFA_ASSURANCE] = {
        "version": 1,
        "user_pk": str(user.pk),
        "verified_at": _now(),
        "method": verification.method,
    }
    return next_url
