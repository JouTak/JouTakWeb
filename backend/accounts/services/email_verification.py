"""Manual e-mail verification requests (the "resend" action)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from accounts.api.errors import raise_structured_error
from accounts.services.email_delivery import (
    ACTIVE_STATUSES,
    describe_delivery,
    latest_confirmation_tracker,
)
from accounts.transport.schemas import EmailDeliveryOut, ResendEmailOut
from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from core.models import EmailVerificationTask
from django.http import HttpRequest
from django.utils import timezone

EMAIL_ADDRESS_MISSING = "EMAIL_ADDRESS_MISSING"
EMAIL_ALREADY_VERIFIED = "EMAIL_ALREADY_VERIFIED"
EMAIL_RESEND_COOLDOWN = "EMAIL_RESEND_COOLDOWN"


class EmailResendCooldownError(Exception):
    """A resend was requested before ``next_allowed_at``."""

    def __init__(self, next_allowed_at: datetime) -> None:
        super().__init__("e-mail resend is on cooldown")
        self.next_allowed_at = next_allowed_at
        remaining = (next_allowed_at - timezone.now()).total_seconds()
        self.retry_after_seconds = max(1, math.ceil(remaining))


def _result(message: str, tracker: EmailVerificationTask) -> ResendEmailOut:
    return ResendEmailOut(
        ok=True,
        message=message,
        delivery=EmailDeliveryOut(**describe_delivery(tracker)),
    )


@dataclass(slots=True)
class EmailVerificationService:
    @staticmethod
    def resend(request: HttpRequest, user) -> ResendEmailOut:
        """Queue a confirmation mail for the user's primary address.

        If a mail is already queued, its current state is returned and
        nothing new is queued. Inside the cooldown after the previous
        mail ``EmailResendCooldownError`` is raised.
        """
        address = EmailAddress.objects.filter(user=user, primary=True).first()
        if address is None:
            raise_structured_error(
                400,
                detail="No email address to verify",
                error_code=EMAIL_ADDRESS_MISSING,
            )
        if address.verified:
            raise_structured_error(
                400,
                detail="Email is already verified",
                error_code=EMAIL_ALREADY_VERIFIED,
            )

        tracker = latest_confirmation_tracker(user, address.email)
        if tracker is not None and tracker.status in ACTIVE_STATUSES:
            return _result(
                "Письмо уже находится в очереди на отправку", tracker
            )
        if (
            tracker is not None
            and tracker.next_allowed_at is not None
            and tracker.next_allowed_at > timezone.now()
        ):
            raise EmailResendCooldownError(tracker.next_allowed_at)

        # The adapter queues the mail (and re-checks the same rules under
        # a lock, so parallel requests still produce a single mail).
        get_adapter(request).send_confirmation_mail(
            request, EmailConfirmationHMAC(address), False
        )
        tracker = latest_confirmation_tracker(user, address.email)
        if tracker is None:
            raise RuntimeError("confirmation mail was not queued")
        return _result("Письмо добавлено в очередь", tracker)
