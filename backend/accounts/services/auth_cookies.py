from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse


def refresh_cookie_name() -> str:
    return settings.JWT_REFRESH_COOKIE_NAME


def get_refresh_cookie(request: HttpRequest) -> str:
    return request.COOKIES.get(refresh_cookie_name(), "")


def set_refresh_cookie(response: HttpResponse, refresh_token: str) -> None:
    response.set_cookie(
        refresh_cookie_name(),
        refresh_token,
        max_age=settings.JWT_REFRESH_COOKIE_MAX_AGE,
        path=settings.JWT_REFRESH_COOKIE_PATH,
        domain=settings.JWT_REFRESH_COOKIE_DOMAIN or None,
        secure=settings.JWT_REFRESH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
    )


def delete_refresh_cookie(response: HttpResponse) -> None:
    response.delete_cookie(
        refresh_cookie_name(),
        path=settings.JWT_REFRESH_COOKIE_PATH,
        domain=settings.JWT_REFRESH_COOKIE_DOMAIN or None,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
    )
