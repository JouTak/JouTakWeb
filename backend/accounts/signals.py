"""Cancel confirmation mails that are no longer needed."""

from __future__ import annotations

from accounts.services.email_delivery import ACTIVE_STATUSES
from allauth.account.models import EmailAddress
from core.models import EmailVerificationTask
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone


def cancel_pending_confirmations(email: str) -> int:
    """Cancel queued confirmation mails for ``email``; returns the count.

    A mail that a worker is sending right now cannot be recalled; the
    worker also re-checks the address before it sends.
    """
    return EmailVerificationTask.objects.filter(
        email__iexact=email,
        kind__in=EmailVerificationTask.CONFIRMATION_KINDS,
        status__in=ACTIVE_STATUSES,
    ).update(
        status=EmailVerificationTask.Status.CANCELLED,
        next_attempt_at=None,
        locked_until=None,
        updated_at=timezone.now(),
    )


@receiver(
    post_save,
    sender=EmailAddress,
    dispatch_uid="accounts.verified_email_cancels_confirmation",
)
def cancel_confirmation_when_verified(sender, instance, **kwargs) -> None:
    # Covers every way an address becomes verified: the confirmation
    # link, a social login, the admin.
    if instance.verified:
        cancel_pending_confirmations(instance.email)


@receiver(
    post_delete,
    sender=EmailAddress,
    dispatch_uid="accounts.deleted_email_cancels_confirmation",
)
def cancel_confirmation_when_deleted(sender, instance, **kwargs) -> None:
    # An address replaced or removed (including with the account).
    cancel_pending_confirmations(instance.email)
