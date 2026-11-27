from __future__ import annotations

from datetime import timedelta
from io import StringIO

from accounts.apps import EMAIL_DISPATCH_SCHEDULE_NAME
from accounts.tasks import WORKER_HEARTBEAT_CACHE_KEY
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone
from django_q.models import Schedule


class CheckEmailWorkerTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        cache.delete(WORKER_HEARTBEAT_CACHE_KEY)

    def schedule(self):
        return Schedule.objects.filter(name=EMAIL_DISPATCH_SCHEDULE_NAME)

    def test_scheduled_dispatcher_is_healthy(self) -> None:
        self.schedule().update(next_run=timezone.now() + timedelta(minutes=1))
        stdout = StringIO()

        call_command("check_email_worker", stdout=stdout)

        self.assertIn("ok", stdout.getvalue())

    def test_stale_schedule_means_the_worker_is_down(self) -> None:
        self.schedule().update(next_run=timezone.now() - timedelta(minutes=11))

        with self.assertRaises(CommandError):
            call_command("check_email_worker")

    def test_fresh_heartbeat_is_healthy_even_if_the_schedule_lags(
        self,
    ) -> None:
        self.schedule().update(next_run=timezone.now() - timedelta(hours=2))
        cache.set(WORKER_HEARTBEAT_CACHE_KEY, timezone.now().isoformat())

        call_command("check_email_worker")

    def test_old_heartbeat_and_stale_schedule_mean_the_worker_is_down(
        self,
    ) -> None:
        old = timezone.now() - timedelta(minutes=11)
        self.schedule().update(next_run=old)
        cache.set(WORKER_HEARTBEAT_CACHE_KEY, old.isoformat())

        with self.assertRaises(CommandError):
            call_command("check_email_worker")

    def test_garbage_heartbeat_is_ignored(self) -> None:
        self.schedule().update(next_run=timezone.now() + timedelta(minutes=1))
        cache.set(WORKER_HEARTBEAT_CACHE_KEY, "not a date")

        call_command("check_email_worker")

    def test_missing_schedule_is_reported(self) -> None:
        self.schedule().delete()

        with self.assertRaises(CommandError):
            call_command("check_email_worker")
