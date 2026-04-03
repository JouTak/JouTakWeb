from __future__ import annotations

import os
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


def _normalize_domain(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""
    if "://" not in value:
        return value.strip("/")
    parsed = urlparse(value)
    return (parsed.netloc or parsed.path or "").strip("/")


class Command(BaseCommand):
    help = "Sync django.contrib.sites Site(id=SITE_ID) using env/domain config"

    def handle(self, *args, **options):
        configured_domain = os.environ.get("DJANGO_SITE_DOMAIN", "")
        configured_name = os.environ.get("DJANGO_SITE_NAME", "")
        default_domain = getattr(settings, "FRONTEND_BASE_URL", "")

        domain = _normalize_domain(configured_domain) or _normalize_domain(
            default_domain
        )
        if not domain:
            self.stdout.write("sync_site skipped: no domain configured")
            return

        name = (configured_name or "").strip() or domain
        site_id = int(getattr(settings, "SITE_ID", 1) or 1)
        site, _ = Site.objects.update_or_create(
            id=site_id,
            defaults={
                "domain": domain,
                "name": name,
            },
        )
        self.stdout.write(
            "Updated "
            f"Site(id={site.id}, domain={site.domain}, name={site.name})"
        )
