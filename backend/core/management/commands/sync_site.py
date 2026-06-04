from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError


def _extract_domain(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"//{raw}")
    return (parsed.netloc or parsed.path).strip("/")


class Command(BaseCommand):
    help = "Synchronize django.contrib.sites Site from settings or CLI args."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--site-id", type=int, default=None)
        parser.add_argument("--domain", default=None)
        parser.add_argument("--name", default=None)

    def handle(self, *args, **options) -> None:
        if "django.contrib.sites" not in settings.INSTALLED_APPS:
            raise CommandError("django.contrib.sites is not installed")

        site_id = options["site_id"] or settings.SITE_ID
        domain = (
            _extract_domain(options["domain"] or "")
            or _extract_domain(getattr(settings, "SITE_DOMAIN", ""))
            or _extract_domain(getattr(settings, "FRONTEND_BASE_URL", ""))
            or "localhost"
        )
        name = (options["name"] or getattr(settings, "SITE_NAME", "")).strip()
        if not name:
            name = domain

        site, created = Site.objects.update_or_create(
            id=site_id,
            defaults={"domain": domain, "name": name},
        )

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} Site(id={site.id}, domain={site.domain},"
                f" name={site.name})"
            )
        )
