from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import urlencode
from django.urls import reverse, NoReverseMatch
from django.conf import settings as dj_settings
from allauth.socialaccount.providers import registry
from allauth.socialaccount.models import SocialApp
from ninja.errors import HttpError


@dataclass(slots=True)
class OAuthService:
    @staticmethod
    def configured_provider_ids() -> set[str]:
        from_db = set(SocialApp.objects.values_list("provider", flat=True))
        from_settings = set()
        providers_cfg = (
            getattr(dj_settings, "SOCIALACCOUNT_PROVIDERS", {}) or {}
        )
        for pid, conf in providers_cfg.items():
            apps = conf.get("APPS") or conf.get("apps")
            if apps:
                from_settings.add(pid)
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
            except NoReverseMatch:
                raise HttpError(404, "unknown provider")
        method = (
            "GET"
            if getattr(dj_settings, "SOCIALACCOUNT_LOGIN_ON_GET", False)
            else "POST"
        )
        url = f"{path}?{urlencode({'process': 'connect', 'next': next_path})}"
        return {"authorize_url": url, "method": method}
