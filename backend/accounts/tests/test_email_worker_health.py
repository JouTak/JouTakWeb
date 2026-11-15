from __future__ import annotations

from datetime import timedelta
from io import StringIO

from accounts.apps import EMAIL_DISPATCH_SCHEDULE_NAME
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone
from django_q.models import Schedule


class CheckEmailWorkerTests(TestCase):
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

    def test_missing_schedule_is_reported(self) -> None:
        self.schedule().delete()

        with self.assertRaises(CommandError):
            call_command("check_email_worker")
