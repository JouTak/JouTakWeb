from __future__ import annotations

import re
import smtplib
import time
from unittest import mock
from urllib.parse import unquote

from accounts.tasks import send_email_task, send_plain_email_task
from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from core.models import EmailVerificationTask
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase

Kind = EmailVerificationTask.Kind
Status = EmailVerificationTask.Status


def make_user(
    username: str = "queue_user",
    email: str = "queue@example.com",
    *,
    verified: bool = False,
):
    user = get_user_model().objects.create_user(
        username=username, email=email, password="StrongPass123!"
    )
    address = EmailAddress.objects.create(
        user=user, email=email, primary=True, verified=verified
    )
    return user, address


def make_tracker(user, email, kind=Kind.EMAIL_CONFIRMATION, **extra):
    return EmailVerificationTask.objects.create(
        user=user, email=email, kind=kind, **extra
    )


def message_text(message) -> str:
    parts = [message.body]
    parts.extend(alt[0] for alt in message.alternatives)
    return "\n".join(parts)


class EnqueueTests(TestCase):
    def test_confirmation_queues_only_the_tracker_id(self) -> None:
        _user, address = make_user()
        confirmation = EmailConfirmationHMAC(address)

        with mock.patch(
            "accounts.adapters.async_task", return_value="task-1"
        ) as queued:
            get_adapter().send_confirmation_mail(None, confirmation, False)

        tracker = EmailVerificationTask.objects.get(email=address.email)
        queued.assert_called_once_with(
            "accounts.tasks.send_email_task", tracker_id=tracker.id
        )
        self.assertEqual(tracker.kind, Kind.EMAIL_CONFIRMATION)
        self.assertEqual(tracker.status, Status.WAITING)
        self.assertEqual(tracker.task_id, "task-1")
        self.assertEqual(mail.outbox, [])

    def test_signup_confirmation_has_its_own_kind(self) -> None:
        _user, address = make_user()
        confirmation = EmailConfirmationHMAC(address)

        with mock.patch("accounts.adapters.async_task", return_value="t"):
            get_adapter().send_confirmation_mail(None, confirmation, True)

        tracker = EmailVerificationTask.objects.get(email=address.email)
        self.assertEqual(tracker.kind, Kind.EMAIL_CONFIRMATION_SIGNUP)

    def test_password_reset_does_not_overwrite_confirmation(self) -> None:
        user, address = make_user()
        confirmation = EmailConfirmationHMAC(address)
        adapter = get_adapter()

        with mock.patch("accounts.adapters.async_task", return_value="t"):
            adapter.send_confirmation_mail(None, confirmation, False)
            adapter.send_password_reset_mail(user, address.email, {})

        kinds = set(
            EmailVerificationTask.objects.filter(
                email=address.email
            ).values_list("kind", flat=True)
        )
        self.assertEqual(kinds, {Kind.EMAIL_CONFIRMATION, Kind.PASSWORD_RESET})

    def test_new_request_reopens_a_sent_tracker(self) -> None:
        user, address = make_user()
        make_tracker(user, address.email, status=Status.SENT)
        confirmation = EmailConfirmationHMAC(address)

        with mock.patch("accounts.adapters.async_task", return_value="t"):
            get_adapter().send_confirmation_mail(None, confirmation, False)

        tracker = EmailVerificationTask.objects.get(email=address.email)
        self.assertEqual(tracker.status, Status.WAITING)

    def test_mail_without_secrets_is_queued_as_rendered_message(self) -> None:
        context = {
            "signup_url": "https://joutak.ru/login",
            "password_reset_url": "https://joutak.ru/reset-password",
        }

        with mock.patch("accounts.adapters.async_task") as queued:
            get_adapter().send_mail(
                "account/email/unknown_account", "nobody@example.com", context
            )

        queued.assert_called_once()
        args, kwargs = queued.call_args
        self.assertEqual(args, ("accounts.tasks.send_plain_email_task",))
        self.assertEqual(kwargs["to"], ["nobody@example.com"])
        self.assertEqual(EmailVerificationTask.objects.count(), 0)
        self.assertEqual(mail.outbox, [])


class WorkerTests(TestCase):
    def test_confirmation_link_is_generated_at_send_time(self) -> None:
        user, address = make_user()
        tracker = make_tracker(user, address.email)

        send_email_task(tracker.id)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, [address.email])
        match = re.search(
            r"confirm-email\?key=([A-Za-z0-9_\-:%]+)", message_text(message)
        )
        self.assertIsNotNone(match, message_text(message))
        key = unquote(match.group(1))
        confirmation = EmailConfirmationHMAC.from_key(key)
        self.assertIsNotNone(confirmation, key)
        self.assertEqual(confirmation.email_address.pk, address.pk)
        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.SENT)

    def test_mail_that_waited_for_days_gets_a_valid_link(self) -> None:
        user, address = make_user()
        tracker = make_tracker(user, address.email)
        key_made_at_queue_time = EmailConfirmationHMAC(address).key
        in_ten_days = time.time() + 10 * 24 * 3600

        # Only the signing module sees the later time (the default link
        # lifetime is three days).
        with mock.patch("django.core.signing.time") as signing_time:
            signing_time.time.return_value = in_ten_days
            send_email_task(tracker.id)
            match = re.search(
                r"confirm-email\?key=([A-Za-z0-9_\-:%]+)",
                message_text(mail.outbox[0]),
            )
            self.assertIsNotNone(match)
            fresh = EmailConfirmationHMAC.from_key(unquote(match.group(1)))
            stale = EmailConfirmationHMAC.from_key(key_made_at_queue_time)

        self.assertIsNotNone(fresh)
        self.assertIsNone(stale)

    def test_password_reset_token_is_generated_at_send_time(self) -> None:
        user, address = make_user()
        tracker = make_tracker(user, address.email, Kind.PASSWORD_RESET)

        send_email_task(tracker.id)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [address.email])
        self.assertIn("reset-password?key=", message_text(mail.outbox[0]))
        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.SENT)

    def test_verified_address_cancels_the_mail(self) -> None:
        user, address = make_user(verified=True)
        tracker = make_tracker(user, address.email)

        send_email_task(tracker.id)

        self.assertEqual(mail.outbox, [])
        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.CANCELLED)

    def test_replaced_address_cancels_the_mail(self) -> None:
        user, _address = make_user()
        tracker = make_tracker(user, "old@example.com")

        send_email_task(tracker.id)

        self.assertEqual(mail.outbox, [])
        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.CANCELLED)

    def test_inactive_user_does_not_get_a_reset_mail(self) -> None:
        user, address = make_user()
        user.is_active = False
        user.save(update_fields=["is_active"])
        tracker = make_tracker(user, address.email, Kind.PASSWORD_RESET)

        send_email_task(tracker.id)

        self.assertEqual(mail.outbox, [])
        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.CANCELLED)

    def test_finished_tracker_is_not_sent_again(self) -> None:
        user, address = make_user()
        tracker = make_tracker(user, address.email, status=Status.SENT)

        send_email_task(tracker.id)

        self.assertEqual(mail.outbox, [])

    def test_unknown_tracker_is_ignored(self) -> None:
        send_email_task(987654)

        self.assertEqual(mail.outbox, [])

    def test_smtp_failure_marks_retry(self) -> None:
        user, address = make_user()
        tracker = make_tracker(user, address.email)

        with mock.patch(
            "django.core.mail.EmailMessage.send",
            side_effect=smtplib.SMTPServerDisconnected("down"),
        ):
            send_email_task(tracker.id)

        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.RETRYING)
        self.assertIsNotNone(tracker.next_attempt_at)

    def test_timeout_is_treated_as_a_temporary_failure(self) -> None:
        user, address = make_user()
        tracker = make_tracker(user, address.email)

        with mock.patch(
            "django.core.mail.EmailMessage.send",
            side_effect=TimeoutError("timed out"),
        ):
            send_email_task(tracker.id)

        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.RETRYING)

    def test_retrying_tracker_is_sent_after_recovery(self) -> None:
        user, address = make_user()
        tracker = make_tracker(user, address.email, status=Status.RETRYING)

        send_email_task(tracker.id)

        self.assertEqual(len(mail.outbox), 1)
        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.SENT)
        self.assertIsNone(tracker.next_attempt_at)

    def test_plain_task_sends_the_rendered_message(self) -> None:
        send_plain_email_task(
            to=["nobody@example.com"],
            subject="Subject",
            body="Body",
            alternatives=[("<p>Body</p>", "text/html")],
        )

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["nobody@example.com"])
        self.assertEqual(message.subject, "Subject")
        self.assertEqual(message.alternatives[0][1], "text/html")
