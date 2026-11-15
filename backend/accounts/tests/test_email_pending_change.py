from __future__ import annotations

from datetime import timedelta
from unittest import mock

from accounts.services.account_status import AccountStatusService
from accounts.tests.base import APITestCase
from allauth.account.models import EmailAddress
from core.models import EmailVerificationTask
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone

User = get_user_model()
Status = EmailVerificationTask.Status


@override_settings(EMAIL_RESEND_COOLDOWN_SECONDS=60)
class PendingChangeApiTests(APITestCase):
    def create_user(self, *, verified: bool) -> tuple[User, str]:
        payload = self.signup_and_auth()
        user = User.objects.get(email=payload["email"].lower())
        if verified:
            EmailAddress.objects.filter(user=user).update(
                verified=True, primary=True
            )
        return user, payload["session_token"]

    def change_email(self, token: str, new_email: str):
        return self.headless_post_json(
            "/account/email",
            {"email": new_email},
            **self.auth_headers(token),
        )

    def account_status(self, token: str) -> dict:
        response = self.client.get(
            self.api("/account/status"), **self.auth_headers(token)
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def resend(self, token: str):
        return self.post_json(
            "/account/email/resend", **self.auth_headers(token)
        )

    def test_verified_user_resends_to_the_pending_address(self) -> None:
        user, token = self.create_user(verified=True)
        new_email = self.unique_email("pending")

        changed = self.change_email(token, new_email)
        self.assertEqual(changed.status_code, 200, changed.content)

        # Delivery status of the NEW address; the old one stays verified.
        status = self.account_status(token)
        self.assertTrue(status["email_verified"])
        self.assertEqual(status["email_delivery"]["email"], new_email)
        self.assertEqual(status["email_delivery"]["status"], "waiting")

        # A repeated request returns the queued mail, nothing new.
        resend = self.resend(token)
        self.assertEqual(resend.status_code, 200, resend.content)
        self.assertEqual(resend.json()["delivery"]["email"], new_email)
        self.assertEqual(
            EmailVerificationTask.objects.filter(email=new_email).count(), 1
        )

        # Right after a sent mail the cooldown of the new address applies.
        EmailVerificationTask.objects.filter(email=new_email).update(
            status=Status.SENT,
            next_allowed_at=timezone.now() + timedelta(seconds=45),
        )
        limited = self.resend(token)
        self.assertEqual(limited.status_code, 429, limited.content)
        self.assertEqual(
            limited.json()["error_code"], "EMAIL_RESEND_COOLDOWN"
        )

        EmailVerificationTask.objects.filter(email=new_email).update(
            next_allowed_at=timezone.now() - timedelta(seconds=1)
        )
        with mock.patch(
            "accounts.adapters.async_task", return_value="t"
        ) as queued:
            again = self.resend(token)
        self.assertEqual(again.status_code, 200, again.content)
        queued.assert_called_once()
        self.assertEqual(again.json()["delivery"]["email"], new_email)
        self.assertEqual(again.json()["delivery"]["status"], "waiting")

        # primary and verified were never switched
        primary = EmailAddress.objects.get(user=user, primary=True)
        self.assertTrue(primary.verified)
        AccountStatusService.require_email_verified(user)

    def test_unverified_user_resends_to_the_new_address(self) -> None:
        _user, token = self.create_user(verified=False)
        new_email = self.unique_email("replacement")

        changed = self.change_email(token, new_email)
        self.assertEqual(changed.status_code, 200, changed.content)

        status = self.account_status(token)
        self.assertFalse(status["email_verified"])
        self.assertEqual(status["email_delivery"]["email"], new_email)

        resend = self.resend(token)
        self.assertEqual(resend.status_code, 200, resend.content)
        self.assertEqual(resend.json()["delivery"]["email"], new_email)
        self.assertEqual(resend.json()["delivery"]["status"], "waiting")

    def test_resend_is_rejected_when_nothing_awaits_confirmation(
        self,
    ) -> None:
        _user, token = self.create_user(verified=True)

        response = self.resend(token)

        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(
            response.json()["error_code"], "EMAIL_ALREADY_VERIFIED"
        )
        self.assertIsNone(self.account_status(token)["email_delivery"])
