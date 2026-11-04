from __future__ import annotations

from datetime import timedelta
from unittest import mock

from accounts.services.email_delivery import attempt_delivery
from accounts.tests.base import APITestCase
from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from core.models import EmailVerificationTask
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

User = get_user_model()
Kind = EmailVerificationTask.Kind
Status = EmailVerificationTask.Status


def make_user(email: str = "dedupe@example.com"):
    user = User.objects.create_user(
        username="dedupe_user", email=email, password="StrongPass123!"
    )
    address = EmailAddress.objects.create(
        user=user, email=email, primary=True, verified=False
    )
    return user, address


def request_confirmation(address, *, signup: bool = False) -> None:
    get_adapter().send_confirmation_mail(
        None, EmailConfirmationHMAC(address), signup
    )


@override_settings(EMAIL_RESEND_COOLDOWN_SECONDS=60)
class DedupeTests(TestCase):
    def test_repeated_requests_queue_one_mail(self) -> None:
        _user, address = make_user()

        with mock.patch(
            "accounts.adapters.async_task", return_value="t"
        ) as queued:
            request_confirmation(address)
            request_confirmation(address)
            request_confirmation(address)

        self.assertEqual(queued.call_count, 1)
        self.assertEqual(
            EmailVerificationTask.objects.filter(email=address.email).count(),
            1,
        )

    def test_signup_and_manual_requests_share_one_mail(self) -> None:
        _user, address = make_user()

        with mock.patch(
            "accounts.adapters.async_task", return_value="t"
        ) as queued:
            request_confirmation(address, signup=True)
            request_confirmation(address, signup=False)

        self.assertEqual(queued.call_count, 1)
        tracker = EmailVerificationTask.objects.get(email=address.email)
        self.assertEqual(tracker.kind, Kind.EMAIL_CONFIRMATION_SIGNUP)

    def test_first_request_sets_the_cooldown(self) -> None:
        _user, address = make_user()
        before = timezone.now()

        with mock.patch("accounts.adapters.async_task", return_value="t"):
            request_confirmation(address)

        tracker = EmailVerificationTask.objects.get(email=address.email)
        wait = (tracker.next_allowed_at - before).total_seconds()
        self.assertTrue(59 <= wait <= 70, wait)

    def test_request_inside_the_cooldown_is_ignored(self) -> None:
        user, address = make_user()
        tracker = EmailVerificationTask.objects.create(
            user=user,
            email=address.email,
            kind=Kind.EMAIL_CONFIRMATION,
            status=Status.SENT,
            next_allowed_at=timezone.now() + timedelta(seconds=30),
        )

        with mock.patch("accounts.adapters.async_task") as queued:
            request_confirmation(address)

        queued.assert_not_called()
        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.SENT)

    def test_request_after_the_cooldown_reopens_the_mail(self) -> None:
        user, address = make_user()
        EmailVerificationTask.objects.create(
            user=user,
            email=address.email,
            kind=Kind.EMAIL_CONFIRMATION_SIGNUP,
            status=Status.SENT,
            next_allowed_at=timezone.now() - timedelta(seconds=1),
        )

        with mock.patch(
            "accounts.adapters.async_task", return_value="t"
        ) as queued:
            request_confirmation(address, signup=False)

        queued.assert_called_once()
        tracker = EmailVerificationTask.objects.get(email=address.email)
        self.assertEqual(tracker.kind, Kind.EMAIL_CONFIRMATION)
        self.assertEqual(tracker.status, Status.WAITING)

    def test_password_reset_requests_are_deduplicated(self) -> None:
        user, address = make_user()
        adapter = get_adapter()

        with mock.patch(
            "accounts.adapters.async_task", return_value="t"
        ) as queued:
            adapter.send_password_reset_mail(user, address.email, {})
            adapter.send_password_reset_mail(user, address.email, {})

        self.assertEqual(queued.call_count, 1)

    def test_sent_mail_starts_the_cooldown(self) -> None:
        user, address = make_user()
        tracker = EmailVerificationTask.objects.create(
            user=user, email=address.email, kind=Kind.EMAIL_CONFIRMATION
        )
        before = timezone.now()

        attempt_delivery(tracker.id)

        self.assertEqual(len(mail.outbox), 1)
        tracker.refresh_from_db()
        self.assertEqual(tracker.status, Status.SENT)
        wait = (tracker.next_allowed_at - before).total_seconds()
        self.assertTrue(59 <= wait <= 70, wait)


@override_settings(EMAIL_RESEND_COOLDOWN_SECONDS=60)
class ResendApiTests(APITestCase):
    def create_authenticated_user(self) -> tuple[User, str]:
        payload = self.signup_and_auth()
        user = User.objects.get(email=payload["email"].lower())
        return user, payload["session_token"]

    def resend(self, token: str):
        return self.post_json(
            "/account/email/resend", **self.auth_headers(token)
        )

    def set_tracker(self, user: User, **fields: object) -> None:
        EmailVerificationTask.objects.filter(user=user).delete()
        EmailVerificationTask.objects.create(
            user=user,
            email=user.email,
            kind=Kind.EMAIL_CONFIRMATION,
            **fields,
        )

    def test_resend_requires_authentication(self) -> None:
        response = self.post_json("/account/email/resend")

        self.assertEqual(response.status_code, 401)

    def test_resend_while_queued_returns_the_current_status(self) -> None:
        user, token = self.create_authenticated_user()

        first = self.resend(token)
        second = self.resend(token)

        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(second.status_code, 200, second.content)
        self.assertEqual(second.json()["delivery"]["status"], "waiting")
        self.assertEqual(
            EmailVerificationTask.objects.filter(user=user).count(), 1
        )

    def test_resend_inside_the_cooldown_returns_429(self) -> None:
        user, token = self.create_authenticated_user()
        self.set_tracker(
            user,
            status=Status.SENT,
            next_allowed_at=timezone.now() + timedelta(seconds=45),
        )

        response = self.resend(token)

        self.assertEqual(response.status_code, 429, response.content)
        data = response.json()
        self.assertEqual(data["error_code"], "EMAIL_RESEND_COOLDOWN")
        self.assertTrue(1 <= data["retry_after_seconds"] <= 45)
        self.assertIn("next_allowed_at", data)
        self.assertEqual(
            response.headers["Retry-After"], str(data["retry_after_seconds"])
        )

    def test_resend_after_the_cooldown_queues_a_new_mail(self) -> None:
        user, token = self.create_authenticated_user()
        self.set_tracker(
            user,
            status=Status.SENT,
            next_allowed_at=timezone.now() - timedelta(seconds=1),
        )

        with mock.patch(
            "accounts.adapters.async_task", return_value="t"
        ) as queued:
            response = self.resend(token)

        self.assertEqual(response.status_code, 200, response.content)
        queued.assert_called_once()
        delivery = response.json()["delivery"]
        self.assertEqual(delivery["status"], "waiting")
        self.assertIsNotNone(delivery["next_allowed_at"])

    def test_resend_for_a_verified_email_is_rejected(self) -> None:
        user, token = self.create_authenticated_user()
        EmailAddress.objects.filter(user=user).update(
            verified=True, primary=True
        )

        response = self.resend(token)

        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(
            response.json()["error_code"], "EMAIL_ALREADY_VERIFIED"
        )

    def test_status_reports_the_delivery_and_next_allowed_time(self) -> None:
        _user, token = self.create_authenticated_user()
        self.resend(token)

        response = self.client.get(
            self.api("/account/status"), **self.auth_headers(token)
        )

        self.assertEqual(response.status_code, 200, response.content)
        delivery = response.json()["email_delivery"]
        self.assertEqual(delivery["status"], "waiting")
        self.assertIn("next_allowed_at", delivery)
