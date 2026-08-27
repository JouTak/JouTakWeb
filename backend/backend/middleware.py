from __future__ import annotations

import logging
from urllib.parse import urlencode, urlsplit
from uuid import uuid4

from accounts.services.admin_mfa import (
    admin_request_has_mfa_assurance,
    safe_admin_next,
)
from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.core.exceptions import DisallowedHost
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from observability.logging import (
    clear_request_log_context,
    set_request_log_context,
)

ADMIN_ALLOWED_PREFIXES = ("/admin/", "/static/", "/media/")
API_BLOCKED_PREFIXES = ("/admin/", "/static/admin/")
REQUEST_ID_HEADER = "X-Request-ID"
SAFE_HTTP_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

logger = logging.getLogger(__name__)


def _normalized_host(host: str | None) -> str:
    return (host or "").split(":", 1)[0].lower()


def is_admin_host(host: str | None) -> bool:
    return _normalized_host(host) in {
        _normalized_host(value) for value in settings.DJANGO_ADMIN_HOSTS
    }


def is_api_host(host: str | None) -> bool:
    return _normalized_host(host) in {
        _normalized_host(value) for value in settings.DJANGO_API_HOSTS
    }


def is_admin_path(path: str) -> bool:
    return path == "/" or any(
        path == prefix[:-1] or path.startswith(prefix)
        for prefix in ADMIN_ALLOWED_PREFIXES
    )


def is_admin_mfa_path(path: str) -> bool:
    """Paths that require completed MFA (excludes login and MFA verify)."""
    return (
        path.startswith("/admin/")
        and not path.startswith("/admin/login/")
        and not path.startswith("/admin/mfa-verify/")
    )


def _origin_parts(
    value: str,
    *,
    allow_path: bool,
) -> tuple[str, str, int | None] | None:
    if (
        not value
        or value != value.strip()
        or any(
            ord(character) < 32 or ord(character) == 127 for character in value
        )
    ):
        return None
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    hostname = parsed.hostname
    if (
        parsed.scheme not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None

    canonical_host = hostname.lower()
    if ":" in canonical_host:
        canonical_host = f"[{canonical_host}]"
    canonical_netloc = canonical_host
    if port is not None:
        canonical_netloc = f"{canonical_netloc}:{port}"
    canonical_origin = f"{parsed.scheme}://{canonical_netloc}"

    if not allow_path:
        # urlsplit() discards empty query/fragment delimiters and treats a
        # trailing colon as a netloc with no port.  Exact lexical equality is
        # therefore required for an Origin value, not just tuple equality.
        if value != canonical_origin:
            return None
    elif (
        parsed.netloc != canonical_netloc
        or (parsed.path and not parsed.path.startswith("/"))
        or "#" in value
        or ("?" in value and not parsed.query)
    ):
        return None

    return parsed.scheme, hostname.lower(), port


def admin_request_has_exact_origin(request: HttpRequest) -> bool:
    """Bind unsafe admin requests to the exact privileged browser origin."""
    expected_origin = f"{request.scheme}://{request.get_host().lower()}"
    expected = _origin_parts(
        expected_origin,
        allow_path=False,
    )
    if (
        expected is None
        or expected_origin not in settings.WEBAUTHN_ADMIN_ORIGINS
    ):
        return False

    origin = request.headers.get("Origin")
    if origin is not None:
        return _origin_parts(origin, allow_path=False) == expected

    referer = request.headers.get("Referer")
    if referer is None:
        return False
    return _origin_parts(referer, allow_path=True) == expected


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = (
            request.headers.get(REQUEST_ID_HEADER)
            or request.META.get("HTTP_X_REQUEST_ID")
            or uuid4().hex
        )
        request.request_id = request_id
        try:
            request_host = _normalized_host(request.get_host())
        except DisallowedHost:
            # HostRoutingMiddleware remains responsible for rejecting the
            # request.  Do not let observability run ahead of Django's normal
            # exception-to-response/security middleware envelope.
            request_host = "<invalid>"
        token = set_request_log_context(
            request_id=request_id,
            request_host=request_host,
            request_path=request.path,
        )
        try:
            response = self.get_response(request)
        finally:
            clear_request_log_context(token)
        response[REQUEST_ID_HEADER] = request_id
        return response


class HostRoutingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        host = request.get_host()
        path = request.path

        if is_admin_host(host):
            if path == "/":
                return redirect("/admin/")
            if not is_admin_path(path):
                return HttpResponseForbidden(
                    "Admin host exposes only admin assets."
                )

        if is_api_host(host) and any(
            path == prefix[:-1] or path.startswith(prefix)
            for prefix in API_BLOCKED_PREFIXES
        ):
            return HttpResponseForbidden(
                "Admin surface is not available on this host."
            )

        # Block admin paths/assets on unknown hosts (neither admin nor API).
        # This prevents accidental exposure if ALLOWED_HOSTS is too broad.
        if not is_admin_host(host) and not is_api_host(host):
            if any(
                path == prefix[:-1] or path.startswith(prefix)
                for prefix in API_BLOCKED_PREFIXES
            ):
                return HttpResponseForbidden(
                    "Admin surface is not available on this host."
                )

        return self.get_response(request)


class AdminSameOriginMiddleware:
    """Reject unsafe admin requests that did not originate on the admin host.

    Modern browsers send ``Origin`` on unsafe requests. ``Referer`` is accepted
    only as a same-origin fallback for clients that omit ``Origin``. Missing,
    opaque (``null``), malformed, sibling, and unexpected-port values fail
    closed before CSRF processing or an admin view can run.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _rejection_reason(request: HttpRequest) -> str:
        if request.headers.get("Origin") is not None:
            return "origin_mismatch_or_invalid"
        if request.headers.get("Referer") is not None:
            return "referer_mismatch_or_invalid"
        return "origin_context_missing"

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if (
            is_admin_host(request.get_host())
            and (
                request.path == "/admin" or request.path.startswith("/admin/")
            )
            and request.method not in SAFE_HTTP_METHODS
            and not admin_request_has_exact_origin(request)
        ):
            # Never include attacker-controlled Origin/Referer values. The
            # categorical reason is sufficient for alerting and diagnosis.
            logger.warning(
                "admin.origin_rejected",
                extra={
                    "event": "admin.origin_rejected",
                    "reason_code": self._rejection_reason(request),
                    "request_id": getattr(request, "request_id", None),
                    "request_host": _normalized_host(request.get_host()),
                    "request_path": request.path,
                },
            )
            return HttpResponseForbidden(
                "Admin unsafe requests require a same-origin browser context."
            )
        return self.get_response(request)


class AdminMFAEnforcementMiddleware:
    """
    Post-authentication guard: even if a user is logged in, deny access
    to admin pages if they haven't completed MFA verification.

    This acts as a defense-in-depth layer on top of the MFA challenge
    in the admin login flow.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not is_admin_mfa_path(request.path):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if (
            user
            and user.is_authenticated
            and user.is_staff
            and not admin_request_has_mfa_assurance(request)
        ):
            next_url = safe_admin_next(request, request.get_full_path())
            # Fail closed for stale/force-created staff sessions and remove
            # any user-bound assurance before restarting password login.
            auth_logout(request)
            return redirect(f"/admin/login/?{urlencode({'next': next_url})}")

        return self.get_response(request)
