"""Healthcheck for the e-mail worker container (``qcluster``)."""

from __future__ import annotations

from datetime import datetime, timedelta

from accounts.apps import EMAIL_DISPATCH_SCHEDULE_NAME
from accounts.tasks import WORKER_HEARTBEAT_CACHE_KEY
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django_q.models import Schedule

STALE_AFTER = timedelta(minutes=10)


def _is_fresh(moment: datetime, now: datetime) -> bool:
    if timezone.is_naive(moment):
        moment = timezone.make_aware(moment)
    return moment >= now - STALE_AFTER


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

        # The worker records a heartbeat on every task (the dispatcher
        # runs each minute). Right after a start there is none yet; then
        # the schedule decides: catch_up is off, so after downtime its
        # next_run jumps ahead instead of lagging behind.
        now = timezone.now()
        if self._heartbeat_is_fresh(now) or _is_fresh(schedule.next_run, now):
            self.stdout.write("ok")
            return
        raise CommandError("no worker heartbeat, qcluster is down")

    def _heartbeat_is_fresh(self, now: datetime) -> bool:
        raw = cache.get(WORKER_HEARTBEAT_CACHE_KEY)
        if not raw:
            return False
        try:
            return _is_fresh(datetime.fromisoformat(raw), now)
        except ValueError:
            return False
