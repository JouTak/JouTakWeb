"""Cancel queued mails that are no longer needed."""

from __future__ import annotations

from accounts.services.email_delivery import ACTIVE_STATUSES
from allauth.account.models import EmailAddress
from core.models import EmailVerificationTask
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

Kind = EmailVerificationTask.Kind


def cancel_pending_mails(email: str, kinds: tuple[str, ...]) -> int:
    """Cancel queued mails of the given kinds for ``email``.

    Returns the count. A mail that a worker is sending right now cannot be
    recalled; the worker also re-checks the address before it sends.
    """
    return EmailVerificationTask.objects.filter(
        email__iexact=email,
        kind__in=kinds,
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
    # link, a social login, the admin. A password reset mail to a
    # verified address is still wanted, so only confirmations go.
    if instance.verified:
        cancel_pending_mails(
            instance.email, EmailVerificationTask.CONFIRMATION_KINDS
        )


@receiver(
    post_delete,
    sender=EmailAddress,
    dispatch_uid="accounts.deleted_email_cancels_mail",
)
def cancel_mail_when_deleted(sender, instance, **kwargs) -> None:
    # An address replaced or removed (including with the account): no
    # mail, a password reset token included, may go to it any more.
    cancel_pending_mails(
        instance.email,
        (*EmailVerificationTask.CONFIRMATION_KINDS, Kind.PASSWORD_RESET),
    )
