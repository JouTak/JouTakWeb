from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode, urlparse

from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers import registry
from django.conf import settings as dj_settings
from django.urls import NoReverseMatch, reverse
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
        parsed = urlparse(candidate)
        if parsed.scheme or parsed.netloc:
            return default
        if not candidate.startswith("/") or candidate.startswith("//"):
            return default
        return candidate

    @staticmethod
    def configured_provider_ids() -> set[str]:
        from_db = set(SocialApp.objects.values_list("provider", flat=True))
        from_settings = set()
        providers_cfg = (
            getattr(dj_settings, "SOCIALACCOUNT_PROVIDERS", {}) or {}
        )
        for pid, conf in providers_cfg.items():
            if not isinstance(conf, dict):
                continue
            apps = conf.get("APPS") or conf.get("apps")
            if apps:
                from_settings.add(str(pid))
        return from_db | from_settings

    @staticmethod
    def list_providers() -> list[dict]:
        configured = OAuthService.configured_provider_ids()
        return [
            {"id": pid, "name": name}
            for pid, name in registry.as_choices()
            if pid in configured
        ]

    @staticmethod
    def link_provider(
        provider: str, next_path: str = "/account/security"
    ) -> dict:
        safe_next_path = OAuthService.sanitize_next_path(next_path)
        installed = {pid for pid, _ in registry.as_choices()}
        if provider not in installed:
            raise HttpError(404, "unknown provider")
        try:
            path = reverse(
                "socialaccount_login", kwargs={"provider": provider}
            )
        except NoReverseMatch:
            try:
                path = reverse(f"{provider}_login")
            except NoReverseMatch as e:
                raise HttpError(404, "unknown provider") from e
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
