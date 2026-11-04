from __future__ import annotations

import smtplib
import socket
from datetime import timedelta
from unittest import mock

from accounts.apps import (
    EMAIL_DISPATCH_SCHEDULE_NAME,
    ensure_email_dispatch_schedule,
)
from accounts.services.email_delivery import (
    attempt_delivery,
    backoff_seconds,
    is_permanent_error,
)
from accounts.tasks import dispatch_due_emails
from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from core.models import EmailVerificationTask
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

Kind = EmailVerificationTask.Kind
Status = EmailVerificationTask.Status

SMTP_DOWN = smtplib.SMTPServerDisconnected("down")


def make_user(email: str = "retry@example.com"):
    user = get_user_model().objects.create_user(
        username="retry_user", email=email, password="StrongPass123!"
    )
    address = EmailAddress.objects.create(
        user=user, email=email, primary=True, verified=False
    )
    return user, address


def make_tracker(user, email, **extra):
    return EmailVerificationTask.objects.create(
        user=user, email=email, kind=Kind.EMAIL_CONFIRMATION, **extra
    )


def smtp_fails(exc: BaseException):
    return mock.patch("django.core.mail.EmailMessage.send", side_effect=exc)


@override_settings(
    EMAIL_DELIVERY_MAX_ATTEMPTS=3,
    EMAIL_DELIVERY_BACKOFF_BASE_SECONDS=60,
    EMAIL_DELIVERY_BACKOFF_MAX_SECONDS=3600,
    EMAIL_DELIVERY_LEASE_SECONDS=180,
)
class RetryTests(TestCase):
    def test_backoff_doubles_up_to_the_cap(self) -> None:
        delays = [backoff_seconds(n) for n in range(1, 9)]

        self.assertEqual(delays, [60, 120, 240, 480, 960, 1920, 3600, 3600])

    def test_temporary_failure_schedules_a_retry(self) -> None:
        user, address = make_user()
        tracker = make_tracker(user, address.email)
        before = timezone.now()

        with smtp_fails(SMTP_DOWN):
            attempt_delivery(tracker.id)

        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.RETRYING)
        self.assertEqual(tracker.attempts, 1)
        self.assertEqual(tracker.last_error, "SMTPServerDisconnected")
        self.assertIsNone(tracker.locked_until)
        delay = (tracker.next_attempt_at - before).total_seconds()
        self.assertTrue(59 <= delay <= 70, delay)

    def test_delay_grows_with_every_failed_attempt(self) -> None:
        user, address = make_user()
        tracker = make_tracker(
            user, address.email, status=Status.RETRYING, attempts=1
        )
        before = timezone.now()

        with smtp_fails(SMTP_DOWN):
            attempt_delivery(tracker.id)

        tracker.refresh_from_db()
        self.assertEqual(tracker.attempts, 2)
        delay = (tracker.next_attempt_at - before).total_seconds()
        self.assertTrue(119 <= delay <= 130, delay)

    def test_exhausted_attempts_end_in_error(self) -> None:
        user, address = make_user()
        tracker = make_tracker(
            user, address.email, status=Status.RETRYING, attempts=2
        )

        with smtp_fails(SMTP_DOWN):
            attempt_delivery(tracker.id)

        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.ERROR)
        self.assertEqual(tracker.attempts, 3)
        self.assertIsNone(tracker.next_attempt_at)

    def test_permanent_error_stops_at_once(self) -> None:
        user, address = make_user()
        tracker = make_tracker(user, address.email)
        refused = smtplib.SMTPRecipientsRefused(
            {address.email: (550, b"no such user")}
        )

        with smtp_fails(refused):
            attempt_delivery(tracker.id)

        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.ERROR)
        self.assertEqual(tracker.attempts, 1)
        self.assertEqual(tracker.last_error, "SMTPRecipientsRefused")
        self.assertIsNone(tracker.next_attempt_at)

    def test_error_classification(self) -> None:
        cases = [
            (smtplib.SMTPRecipientsRefused({"a": (550, b"x")}), True),
            (smtplib.SMTPRecipientsRefused({"a": (450, b"x")}), False),
            (
                smtplib.SMTPRecipientsRefused(
                    {"a": (550, b"x"), "b": (450, b"y")}
                ),
                False,
            ),
            (smtplib.SMTPDataError(554, b"spam"), True),
            (smtplib.SMTPDataError(451, b"try later"), False),
            (smtplib.SMTPAuthenticationError(535, b"bad credentials"), False),
            (smtplib.SMTPSenderRefused(550, b"no", "a@example.com"), False),
            (smtplib.SMTPServerDisconnected("gone"), False),
            (TimeoutError("timed out"), False),
            (ConnectionRefusedError("refused"), False),
            (socket.gaierror(-2, "unknown host"), False),
        ]
        for exc, expected in cases:
            with self.subTest(exc=repr(exc)):
                self.assertEqual(is_permanent_error(exc), expected)

    def test_retry_is_not_run_before_it_is_due(self) -> None:
        user, address = make_user()
        tracker = make_tracker(
            user,
            address.email,
            status=Status.RETRYING,
            attempts=1,
            next_attempt_at=timezone.now() + timedelta(hours=1),
        )

        attempt_delivery(tracker.id)

        self.assertEqual(mail.outbox, [])
        tracker.refresh_from_db()
        self.assertEqual(tracker.attempts, 1)

    def test_dispatcher_sends_due_retries(self) -> None:
        user, address = make_user()
        tracker = make_tracker(
            user,
            address.email,
            status=Status.RETRYING,
            attempts=1,
            next_attempt_at=timezone.now() - timedelta(minutes=1),
        )

        dispatch_due_emails()

        self.assertEqual(len(mail.outbox), 1)
        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.SENT)
        self.assertEqual(tracker.attempts, 2)
        self.assertIsNone(tracker.next_attempt_at)
        self.assertEqual(tracker.last_error, "")

    def test_dispatcher_ignores_finished_and_not_due(self) -> None:
        user, address = make_user()
        for status in (Status.SENT, Status.ERROR, Status.CANCELLED):
            make_tracker(user, f"{status}@example.com", status=status)
        make_tracker(
            user,
            address.email,
            status=Status.RETRYING,
            next_attempt_at=timezone.now() + timedelta(hours=1),
        )

        dispatch_due_emails()

        self.assertEqual(mail.outbox, [])

    def test_active_lease_blocks_a_second_worker(self) -> None:
        user, address = make_user()
        tracker = make_tracker(
            user,
            address.email,
            attempts=1,
            locked_until=timezone.now() + timedelta(minutes=2),
        )

        attempt_delivery(tracker.id)
        dispatch_due_emails()

        self.assertEqual(mail.outbox, [])
        tracker.refresh_from_db()
        self.assertEqual(tracker.attempts, 1)

    def test_expired_lease_is_taken_over(self) -> None:
        user, address = make_user()
        tracker = make_tracker(
            user,
            address.email,
            attempts=1,
            locked_until=timezone.now() - timedelta(seconds=1),
        )

        dispatch_due_emails()

        self.assertEqual(len(mail.outbox), 1)
        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.SENT)
        self.assertEqual(tracker.attempts, 2)

    def test_second_attempt_does_not_send_twice(self) -> None:
        user, address = make_user()
        tracker = make_tracker(user, address.email)

        attempt_delivery(tracker.id)
        attempt_delivery(tracker.id)

        self.assertEqual(len(mail.outbox), 1)

    def test_new_request_reopens_a_failed_tracker(self) -> None:
        user, address = make_user()
        make_tracker(
            user,
            address.email,
            status=Status.ERROR,
            attempts=5,
            last_error="SMTPRecipientsRefused",
        )
        confirmation = EmailConfirmationHMAC(address)

        with mock.patch("accounts.adapters.async_task", return_value="t"):
            get_adapter().send_confirmation_mail(None, confirmation, False)

        tracker = EmailVerificationTask.objects.get(email=address.email)
        self.assertEqual(tracker.status, Status.WAITING)
        self.assertEqual(tracker.attempts, 0)
        self.assertEqual(tracker.last_error, "")

    def test_failure_log_has_no_address_or_content(self) -> None:
        user, address = make_user()
        tracker = make_tracker(user, address.email)

        with (
            self.assertLogs(
                "accounts.services.email_delivery", level="WARNING"
            ) as logs,
            smtp_fails(SMTP_DOWN),
        ):
            attempt_delivery(tracker.id)

        self.assertEqual(len(logs.records), 1)
        record = logs.records[0]
        self.assertEqual(record.error_class, "SMTPServerDisconnected")
        dumped = " ".join(str(v) for v in record.__dict__.values())
        self.assertNotIn(address.email, dumped)


class DispatchScheduleTests(TestCase):
    def test_schedule_exists_after_migrate(self) -> None:
        schedule_model = apps.get_model("django_q", "Schedule")

        schedule = schedule_model.objects.get(
            name=EMAIL_DISPATCH_SCHEDULE_NAME
        )

        self.assertEqual(schedule.func, "accounts.tasks.dispatch_due_emails")
        self.assertEqual(schedule.schedule_type, schedule_model.MINUTES)
        self.assertEqual(schedule.minutes, 1)
        self.assertEqual(schedule.repeats, -1)

    def test_creating_the_schedule_twice_keeps_one_row(self) -> None:
        schedule_model = apps.get_model("django_q", "Schedule")
        django_q = apps.get_app_config("django_q")

        ensure_email_dispatch_schedule(django_q)
        ensure_email_dispatch_schedule(django_q)

        count = schedule_model.objects.filter(
            name=EMAIL_DISPATCH_SCHEDULE_NAME
        ).count()
        self.assertEqual(count, 1)
