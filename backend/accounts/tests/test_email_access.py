from __future__ import annotations

import smtplib
from unittest import mock

from accounts.api.errors import StructuredHttpError
from accounts.apps import EMAIL_DISPATCH_SCHEDULE_NAME
from accounts.services.account_status import AccountStatusService
from accounts.services.email_delivery import (
    ErrorCategory,
    attempt_delivery,
    classify_delivery_error,
    describe_delivery,
)
from accounts.tasks import record_worker_heartbeat
from accounts.tests.base import APITestCase
from allauth.account.models import EmailAddress
from core.models import EmailVerificationTask
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from django_q.models import Schedule

User = get_user_model()
Kind = EmailVerificationTask.Kind
Status = EmailVerificationTask.Status

SMTP_DOWN = smtplib.SMTPServerDisconnected("mail server is down")


def make_user(email: str = "gate@example.com", *, verified: bool = False):
    user = User.objects.create_user(
        username="gate_user", email=email, password="StrongPass123!"
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


class EmailGateTests(TestCase):
    def test_unverified_email_is_rejected_with_a_reason_code(self) -> None:
        user, _address = make_user()

        with self.assertRaises(StructuredHttpError) as caught:
            AccountStatusService.require_email_verified(user)

        error = caught.exception
        self.assertEqual(error.status_code, 403)
        self.assertEqual(
            error.payload["error_code"], "EMAIL_VERIFICATION_REQUIRED"
        )
        self.assertEqual(
            error.payload["blocking_reasons"], ["EMAIL_VERIFICATION_REQUIRED"]
        )

    def test_verified_email_passes(self) -> None:
        user, _address = make_user(verified=True)

        AccountStatusService.require_email_verified(user)

    def test_mail_failure_does_not_restrict_a_verified_user(self) -> None:
        user, address = make_user(verified=True)
        make_tracker(user, address.email, status=Status.ERROR, attempts=24)

        AccountStatusService.require_email_verified(user)

    def test_another_verified_address_does_not_count(self) -> None:
        user, _address = make_user()
        EmailAddress.objects.create(
            user=user, email="other@example.com", primary=False, verified=True
        )

        with self.assertRaises(StructuredHttpError):
            AccountStatusService.require_email_verified(user)

    def test_confirmation_lifts_the_restriction(self) -> None:
        user, address = make_user()
        with self.assertRaises(StructuredHttpError):
            AccountStatusService.require_email_verified(user)

        address.verified = True
        address.save()

        AccountStatusService.require_email_verified(user)

    def test_email_state_does_not_change_profile_flags(self) -> None:
        user, address = make_user()
        before = AccountStatusService.get_status(user)

        address.verified = True
        address.save()
        after = AccountStatusService.get_status(user)

        self.assertFalse(before["email_verified"])
        self.assertTrue(after["email_verified"])
        for key in (
            "profile_complete",
            "account_active",
            "registration_completed",
            "blocking_reasons",
        ):
            self.assertEqual(before[key], after[key], key)


class CancellationTests(TestCase):
    def test_confirmation_cancels_only_queued_confirmation_mails(
        self,
    ) -> None:
        user, address = make_user()
        queued = make_tracker(user, address.email)
        reset = make_tracker(user, address.email, Kind.PASSWORD_RESET)
        done = make_tracker(
            user,
            address.email,
            Kind.EMAIL_CONFIRMATION_SIGNUP,
            status=Status.SENT,
        )

        address.verified = True
        address.save()

        for tracker in (queued, reset, done):
            tracker.refresh_from_db()
        self.assertEqual(queued.status, Status.CANCELLED)
        self.assertEqual(reset.status, Status.WAITING)
        self.assertEqual(done.status, Status.SENT)
        attempt_delivery(queued.id)
        self.assertEqual(mail.outbox, [])

    def test_deleting_the_address_cancels_the_queued_mail(self) -> None:
        user, address = make_user()
        tracker = make_tracker(
            user, address.email, status=Status.RETRYING, attempts=2
        )

        address.delete()

        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.CANCELLED)

    def test_cancelled_mail_loses_its_error_category(self) -> None:
        user, address = make_user()
        tracker = make_tracker(
            user,
            address.email,
            status=Status.RETRYING,
            attempts=2,
            error_category=ErrorCategory.SMTP_UNAVAILABLE,
        )

        address.delete()

        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.CANCELLED)
        self.assertIsNone(tracker.error_category)

    def test_deleting_the_address_cancels_a_password_reset_mail(self) -> None:
        user, address = make_user()
        tracker = make_tracker(user, address.email, Kind.PASSWORD_RESET)

        address.delete()

        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.CANCELLED)

    def test_deleting_the_account_drops_the_mail(self) -> None:
        user, address = make_user()
        tracker_id = make_tracker(user, address.email).id

        user.delete()

        self.assertFalse(
            EmailVerificationTask.objects.filter(id=tracker_id).exists()
        )
        attempt_delivery(tracker_id)
        self.assertEqual(mail.outbox, [])


@override_settings(EMAIL_DELIVERY_MAX_ATTEMPTS=3)
class DeliveryStateTests(TestCase):
    def test_error_category_is_the_stored_one(self) -> None:
        user, address = make_user()
        cases = [
            (Status.WAITING, None),
            (Status.RETRYING, "smtp_unavailable"),
            (Status.RETRYING, "internal_error"),
            (Status.ERROR, "message_rejected"),
            (Status.ERROR, "worker_interrupted"),
            (Status.SENT, None),
            (Status.CANCELLED, None),
        ]
        for status, stored in cases:
            with self.subTest(status=status, stored=stored):
                tracker = make_tracker(
                    user, address.email, status=status, error_category=stored
                )

                state = describe_delivery(tracker)

                self.assertEqual(state["error_category"], stored)
                self.assertNotIn("is_smtp_down", state)


class OutageApiTests(APITestCase):
    def smtp_down(self):
        return mock.patch(
            "django.core.mail.EmailMessage.send", side_effect=SMTP_DOWN
        )

    def me(self, token: str):
        return self.client.get(
            self.api("/auth/me"), **self.auth_headers(token)
        )

    def test_signup_login_and_profile_work_without_smtp(self) -> None:
        email = self.unique_email("outage")

        with self.smtp_down():
            signup = self.signup(email=email)
            self.assertEqual(signup.status_code, 200, signup.content)
            login = self.login(email=email)
            self.assertEqual(login.status_code, 200, login.content)
            token = self.session_token(login)
            me = self.me(token or "")

        self.assertEqual(me.status_code, 200, me.content)
        data = me.json()
        self.assertFalse(data["email_verified"])
        self.assertEqual(data["email_delivery"]["status"], "waiting")
        self.assertIsNone(data["email_delivery"]["error_category"])

        # The mail server is back: the worker sends the queued mail.
        tracker = EmailVerificationTask.objects.get(email=email.lower())
        attempt_delivery(tracker.id)
        self.assertEqual(len(mail.outbox), 1)
        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.SENT)

    def test_profile_reports_the_error_category_of_a_retry(self) -> None:
        payload = self.signup_and_auth()
        user = User.objects.get(email=payload["email"].lower())
        EmailVerificationTask.objects.filter(user=user).update(
            status=Status.RETRYING,
            error_category=ErrorCategory.SMTP_UNAVAILABLE,
            attempts=2,
            next_attempt_at=timezone.now(),
        )

        data = self.me(payload["session_token"]).json()

        self.assertEqual(data["email_delivery"]["status"], "retrying")
        self.assertEqual(
            data["email_delivery"]["error_category"], "smtp_unavailable"
        )
        self.assertNotIn("is_smtp_down", data["email_delivery"])

    def test_verified_users_are_not_affected_by_the_outage(self) -> None:
        payload = self.signup_and_auth()
        user = User.objects.get(email=payload["email"].lower())
        EmailAddress.objects.filter(user=user).update(
            verified=True, primary=True
        )
        EmailVerificationTask.objects.filter(user=user).update(
            status=Status.ERROR, attempts=24
        )

        response = self.me(payload["session_token"])

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertTrue(data["email_verified"])
        self.assertIsNone(data["email_delivery"])
        AccountStatusService.require_email_verified(user)

    def test_email_change_works_without_smtp(self) -> None:
        payload = self.signup_and_auth()
        new_email = self.unique_email("change")

        with self.smtp_down():
            response = self.headless_post_json(
                "/account/email",
                {"email": new_email},
                **self.auth_headers(payload["session_token"]),
            )

        self.assertEqual(response.status_code, 200, response.content)
        tracker = EmailVerificationTask.objects.get(email=new_email)
        self.assertEqual(tracker.status, Status.WAITING)

    def test_password_reset_works_without_smtp_and_hides_accounts(
        self,
    ) -> None:
        payload = self.signup_and_auth()
        known = payload["email"].lower()
        unknown = self.unique_email("nobody")

        with self.smtp_down():
            for_known = self.headless_post_json(
                "/auth/password/request", {"email": known}
            )
            for_unknown = self.headless_post_json(
                "/auth/password/request", {"email": unknown}
            )

        self.assertEqual(for_known.status_code, 200, for_known.content)
        self.assertEqual(for_unknown.status_code, 200, for_unknown.content)
        self.assertEqual(for_known.json(), for_unknown.json())

        # The mail server is back: the user still gets the reset mail.
        reset = EmailVerificationTask.objects.get(
            email=known, kind=Kind.PASSWORD_RESET
        )
        attempt_delivery(reset.id)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [known])
        self.assertIn("reset-password?key=", message_text(mail.outbox[0]))


class ReviewFixesTests(TestCase):
    def test_error_category_distinguishes_smtp_from_internal(self) -> None:
        self.assertEqual(
            classify_delivery_error(SMTP_DOWN),
            ErrorCategory.SMTP_UNAVAILABLE,
        )
        self.assertEqual(
            classify_delivery_error(RuntimeError("unexpected")),
            ErrorCategory.INTERNAL_ERROR,
        )
        user, address = make_user()
        tracker = make_tracker(
            user,
            address.email,
            status=Status.RETRYING,
            attempts=1,
        )
        tracker.error_category = ErrorCategory.INTERNAL_ERROR
        state = describe_delivery(tracker)
        self.assertEqual(state["error_category"], "internal_error")

    def test_signal_cancellation_is_scoped_to_user(self) -> None:
        user_a, addr_a = make_user()
        user_b = User.objects.create_user(
            username="other_user_b",
            email="other_b@example.com",
            password="Password123!",
        )
        addr_b = EmailAddress.objects.create(
            user=user_b,
            email=addr_a.email,
            verified=False,
            primary=False,
        )
        task_a = make_tracker(
            user_a,
            addr_a.email,
            kind=Kind.PASSWORD_RESET,
            status=Status.WAITING,
        )
        addr_b.delete()
        task_a.refresh_from_db()
        self.assertEqual(task_a.status, Status.WAITING)

    def test_check_email_worker_accepts_fresh_heartbeat(self) -> None:
        Schedule.objects.update_or_create(
            name=EMAIL_DISPATCH_SCHEDULE_NAME,
            defaults={
                "func": "accounts.tasks.dispatch_due_emails",
                "schedule_type": Schedule.MINUTES,
                "minutes": 1,
                "repeats": -1,
                "next_run": timezone.now() - timezone.timedelta(hours=2),
            },
        )
        record_worker_heartbeat()
        call_command("check_email_worker")
