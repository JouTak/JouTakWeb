from __future__ import annotations

from uuid import uuid4

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from observability.logging import (
    clear_request_log_context,
    set_request_log_context,
)

from backend.admin_site import admin_mfa_is_enabled

ADMIN_ALLOWED_PREFIXES = ("/admin/", "/static/", "/media/")
API_BLOCKED_PREFIXES = ("/admin/", "/static/admin/")
REQUEST_ID_HEADER = "X-Request-ID"


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
    return path.startswith("/admin/") and not path.startswith("/admin/login/")


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
        token = set_request_log_context(
            request_id=request_id,
            request_host=_normalized_host(request.get_host()),
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

        return self.get_response(request)


class AdminMFAEnforcementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)
        if not is_admin_mfa_path(request.path):
            return self.get_response(request)

        if user and user.is_authenticated and user.is_staff:
            if not admin_mfa_is_enabled(user):
                return HttpResponseForbidden(
                    "Admin access requires an enrolled MFA factor."
                )

        return self.get_response(request)
