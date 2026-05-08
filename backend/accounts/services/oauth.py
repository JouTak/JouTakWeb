from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from allauth.socialaccount.adapter import (
    get_adapter as get_socialaccount_adapter,
)
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers import registry
from django.conf import settings as dj_settings
from django.core.exceptions import (
    ImproperlyConfigured,
    MultipleObjectsReturned,
)
from django.http import HttpRequest
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from ninja.errors import HttpError


@dataclass(slots=True)
class OAuthService:
    @staticmethod
    def sanitize_next_path(
        next_path: str | None,
        *,
        default: str = "/account/security",
    ) -> str:
        candidate = (next_path or "").strip()
        if not candidate:
            return default
        if not candidate.startswith("/") or candidate.startswith("//"):
            return default
        if not url_has_allowed_host_and_scheme(
            candidate,
            allowed_hosts=None,
            require_https=False,
        ):
            return default
        return candidate

    @staticmethod
    def configured_provider_ids(request: HttpRequest) -> set[str]:
        apps = get_socialaccount_adapter().list_apps(request)
        return {
            str(app.provider) for app in apps if getattr(app, "provider", None)
        }

    @staticmethod
    def list_providers(request: HttpRequest) -> list[dict]:
        configured = OAuthService.configured_provider_ids(request)
        return [
            {"id": provider.id, "name": provider.name}
            for provider in registry.get_class_list()
            if provider.id in configured
        ]

    @staticmethod
    def link_provider(
        request: HttpRequest,
        provider: str,
        next_path: str = "/account/security",
    ) -> dict:
        safe_next_path = OAuthService.sanitize_next_path(next_path)
        provider_class = registry.get_class(provider)
        if provider_class is None:
            raise HttpError(404, "unknown provider")
        if provider_class.uses_apps:
            try:
                get_socialaccount_adapter().get_app(request, provider=provider)
            except (
                SocialApp.DoesNotExist,
                ImproperlyConfigured,
                MultipleObjectsReturned,
            ) as exc:
                raise HttpError(404, "unknown provider") from exc
        try:
            path = reverse(f"{provider}_login")
        except NoReverseMatch as exc:
            raise HttpError(404, "unknown provider") from exc
        method = (
            "GET"
            if getattr(dj_settings, "SOCIALACCOUNT_LOGIN_ON_GET", False)
            else "POST"
        )
        url = (
            f"{path}?"
            f"{urlencode({'process': 'connect', 'next': safe_next_path})}"
        )
        return {"authorize_url": url, "method": method}
