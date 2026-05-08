"""
Unified rate limiting configuration for JouTak API.

Uses django-ratelimit with DatabaseCache backend for shared counters
across Gunicorn workers. All rate limits are configurable via
environment variables with sensible defaults.

Usage in views:
    from backend.ratelimiting import bff_ratelimit, api_ratelimit

    @bff_ratelimit
    def my_bff_view(request): ...

    @api_ratelimit("5/m")
    def my_sensitive_api_view(request): ...

For django-ninja endpoints, use ``ratelimit_method`` as a helper:
    from backend.ratelimiting import ratelimit_method

    ratelimit_method(request, group="auth.refresh", rate="10/m")
"""

from __future__ import annotations

import functools
import logging

from decouple import config
from django.http import JsonResponse
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited

logger = logging.getLogger(__name__)

# ─── Configurable rate limits ───────────────────────────────────────────────

BFF_RATE = config("RATELIMIT_BFF", default="60/m")
BFF_ACCOUNT_RATE = config("RATELIMIT_BFF_ACCOUNT", default="30/m")
API_AUTH_RATE = config("RATELIMIT_API_AUTH", default="10/m")
API_AUTH_SENSITIVE_RATE = config("RATELIMIT_API_AUTH_SENSITIVE", default="5/m")
API_ACCOUNT_DELETE_RATE = config("RATELIMIT_API_ACCOUNT_DELETE", default="3/m")


# ─── Decorators for standard Django views (BFF) ────────────────────────────


def bff_ratelimit(view_func=None, *, rate=None):
    """Rate-limit decorator for BFF views.

    Defaults to BFF_RATE (60/m per IP). Returns JSON 429 on breach.
    """
    effective_rate = rate or BFF_RATE

    def decorator(fn):
        @ratelimit(key="ip", rate=effective_rate, block=False)
        @functools.wraps(fn)
        def wrapper(request, *args, **kwargs):
            if getattr(request, "limited", False):
                logger.warning(
                    "ratelimit.exceeded",
                    extra={
                        "path": request.path,
                        "ip": request.META.get("REMOTE_ADDR"),
                        "rate": effective_rate,
                    },
                )
                return JsonResponse(
                    {
                        "detail": "Too many requests. Please try again later.",
                        "retry_after_seconds": 60,
                    },
                    status=429,
                )
            return fn(request, *args, **kwargs)

        return wrapper

    if view_func is not None:
        return decorator(view_func)
    return decorator


# ─── Imperative check for django-ninja endpoints ───────────────────────────


def ratelimit_method(
    request,
    *,
    group: str,
    rate: str | None = None,
    key: str = "ip",
) -> bool:
    """Check rate limit imperatively inside a django-ninja endpoint.

    Returns True if the request is rate-limited (caller should raise 429).
    Uses django-ratelimit's core ``is_ratelimited`` function.

    Example::

        from backend.ratelimiting import ratelimit_method, API_AUTH_RATE

        def my_endpoint(request):
            if ratelimit_method(request, group="auth.refresh",
                                rate=API_AUTH_RATE):
                raise HttpError(429, "Too many requests")
    """
    from django_ratelimit.core import is_ratelimited

    effective_rate = rate or API_AUTH_RATE
    limited = is_ratelimited(
        request,
        group=group,
        key=key,
        rate=effective_rate,
        increment=True,
    )
    if limited:
        logger.warning(
            "ratelimit.exceeded",
            extra={
                "path": request.path,
                "ip": request.META.get("REMOTE_ADDR"),
                "group": group,
                "rate": effective_rate,
            },
        )
    return limited


# ─── Exception handler for cases where block=True is used ──────────────────


def ratelimit_exception_handler(request, exception):
    """Django view for handling Ratelimited exceptions (if block=True).

    Wire into urls.py or middleware if needed.
    """
    if isinstance(exception, Ratelimited):
        return JsonResponse(
            {
                "detail": "Too many requests. Please try again later.",
                "retry_after_seconds": 60,
            },
            status=429,
        )
    return None
