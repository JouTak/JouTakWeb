"""Healthcheck for the e-mail worker container (``qcluster``)."""

from __future__ import annotations

from datetime import timedelta

from accounts.apps import EMAIL_DISPATCH_SCHEDULE_NAME
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django_q.models import Schedule

# The cluster moves ``next_run`` of the schedule forward every minute;
# a value this far in the past means that nothing is scheduling tasks.
STALE_AFTER = timedelta(minutes=10)


class Command(BaseCommand):
    help = (
        "Exit with an error if the qcluster worker does not schedule the "
        "e-mail dispatcher (container healthcheck, no HTTP port needed)."
    )

    def handle(self, *args, **options) -> None:
        schedule = Schedule.objects.filter(
            name=EMAIL_DISPATCH_SCHEDULE_NAME
        ).first()
        if schedule is None:
            raise CommandError("dispatch schedule is missing, run migrate")
        if schedule.next_run < timezone.now() - STALE_AFTER:
            raise CommandError("dispatch schedule is stale, qcluster is down")
        self.stdout.write("ok")
