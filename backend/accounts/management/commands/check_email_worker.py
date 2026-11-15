"""Healthcheck for the e-mail worker container (``qcluster``)."""

from __future__ import annotations

from datetime import datetime, timedelta

from accounts.apps import EMAIL_DISPATCH_SCHEDULE_NAME
from accounts.tasks import WORKER_HEARTBEAT_CACHE_KEY
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django_q.models import Schedule
from django_q.status import Stat

STALE_AFTER = timedelta(minutes=10)


class Command(BaseCommand):
    help = (
        "Exit with an error if the qcluster worker is not alive or the "
        "e-mail dispatcher schedule is missing."
    )

    def handle(self, *args, **options) -> None:
        schedule = Schedule.objects.filter(
            name=EMAIL_DISPATCH_SCHEDULE_NAME
        ).first()
        if schedule is None:
            raise CommandError("dispatch schedule is missing, run migrate")

        now = timezone.now()
        heartbeat_raw = cache.get(WORKER_HEARTBEAT_CACHE_KEY)
        if heartbeat_raw:
            heartbeat = datetime.fromisoformat(heartbeat_raw)
            if timezone.is_naive(heartbeat):
                heartbeat = timezone.make_aware(heartbeat)
            if heartbeat >= now - STALE_AFTER:
                self.stdout.write("ok")
                return

        clusters = Stat.get_all()
        if any(
            getattr(c, "tob", None) is not None
            and (
                timezone.make_aware(c.tob)
                if timezone.is_naive(c.tob)
                else c.tob
            )
            >= now - STALE_AFTER
            for c in clusters
        ):
            self.stdout.write("ok")
            return

        if schedule.next_run >= now - STALE_AFTER:
            self.stdout.write("ok")
            return

        raise CommandError("dispatch schedule is stale, qcluster is down")
