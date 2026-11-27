"""Cancel queued mails that are no longer needed."""

from __future__ import annotations

from accounts.services.email_delivery import ACTIVE_STATUSES
from allauth.account.models import EmailAddress
from core.models import EmailVerificationTask
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

Kind = EmailVerificationTask.Kind


def cancel_pending_mails(
    user_id: int | None, email: str, kinds: tuple[str, ...]
) -> int:
    """Cancel queued mails of the given kinds for ``user_id`` and ``email``.

    Scoped to ``user_id`` so an action on another account sharing the
    same address under ``ACCOUNT_PREVENT_ENUMERATION`` never cancels this
    user's pending mail.
    """
    if user_id is None:
        return 0
    return EmailVerificationTask.objects.filter(
        user_id=user_id,
        email__iexact=email,
        kind__in=kinds,
        status__in=ACTIVE_STATUSES,
    ).update(
        status=EmailVerificationTask.Status.CANCELLED,
        error_category=None,
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
    if instance.verified:
        cancel_pending_mails(
            instance.user_id,
            instance.email,
            EmailVerificationTask.CONFIRMATION_KINDS,
        )


@receiver(
    post_delete,
    sender=EmailAddress,
    dispatch_uid="accounts.deleted_email_cancels_mail",
)
def cancel_mail_when_deleted(sender, instance, **kwargs) -> None:
    cancel_pending_mails(
        instance.user_id,
        instance.email,
        (*EmailVerificationTask.CONFIRMATION_KINDS, Kind.PASSWORD_RESET),
    )
