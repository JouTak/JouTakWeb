"""Deliver queued account e-mails with freshly generated secrets.

The queue stores only a tracker id. When the worker finally sends the
message, allauth generates the confirmation key or the password reset
token at that moment. A message that waited out an SMTP outage therefore
still carries a valid link, and no secret is kept in the task payload.

Every try goes through ``attempt_delivery``. It claims the tracker with an
atomic UPDATE (a short lease), so several workers never send the same
mail twice, and it records the outcome: sent, cancelled, a retry with an
exponentially growing delay, or a final error.
"""

from __future__ import annotations

import logging
import smtplib
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import timedelta

from allauth.account.adapter import get_adapter
from allauth.account.internal.flows import (
    password_reset as password_reset_flow,
)
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from core.models import EmailVerificationTask
from django.conf import settings
from django.db.models import F, Q
from django.utils import timezone

logger = logging.getLogger(__name__)

Status = EmailVerificationTask.Status
ACTIVE_STATUSES = (Status.WAITING, Status.RETRYING)
DISPATCH_BATCH_SIZE = 50

_DELIVER_NOW: ContextVar[bool] = ContextVar(
    "account_mail_deliver_now", default=False
)

# Server-side or configuration problems: a 5xx here does not mean that
# the message itself is bad, so these are retried like network errors.
_RETRY_EVEN_ON_5XX = (
    smtplib.SMTPAuthenticationError,
    smtplib.SMTPSenderRefused,
    smtplib.SMTPConnectError,
    smtplib.SMTPHeloError,
)


def is_delivering_now() -> bool:
    """True while the worker sends a message (no queueing then)."""
    return _DELIVER_NOW.get()


@contextmanager
def deliver_now() -> Iterator[None]:
    token = _DELIVER_NOW.set(True)
    try:
        yield
    finally:
        _DELIVER_NOW.reset(token)


def is_permanent_error(exc: BaseException) -> bool:
    """True if retrying cannot help (the mail itself is rejected).

    Permanent: every recipient refused with a 5xx code, or a 5xx reply
    to the message data. Everything else (network errors, timeouts, 4xx
    replies, authentication or sender problems) is temporary.
    """
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        codes = [code for code, _ in exc.recipients.values()]
        return bool(codes) and all(500 <= code < 600 for code in codes)
    if isinstance(exc, _RETRY_EVEN_ON_5XX):
        return False
    if isinstance(exc, smtplib.SMTPResponseException):
        return 500 <= exc.smtp_code < 600
    return False


def backoff_seconds(attempts: int) -> int:
    """Delay before the next try, after ``attempts`` tries have failed."""
    delay = settings.EMAIL_DELIVERY_BACKOFF_BASE_SECONDS * 2 ** max(
        attempts - 1, 0
    )
    return min(delay, settings.EMAIL_DELIVERY_BACKOFF_MAX_SECONDS)


def latest_confirmation_tracker(
    user, email: str
) -> EmailVerificationTask | None:
    """The newest address-confirmation mail of the user, if any."""
    return (
        EmailVerificationTask.objects.filter(
            user=user,
            email=email,
            kind__in=EmailVerificationTask.CONFIRMATION_KINDS,
        )
        .order_by("-updated_at", "-id")
        .first()
    )


def describe_delivery(tracker: EmailVerificationTask) -> dict[str, object]:
    """Delivery state in the shape of ``EmailDeliveryOut``.

    ``is_smtp_down`` separates "the mail service is unavailable" from
    "still waiting in the queue": it is true while tries keep failing
    (retrying) and after they ran out of attempts. A mail refused for
    good (an error on the first tries) is not an outage.
    """
    exhausted = (
        tracker.status == Status.ERROR
        and tracker.attempts >= settings.EMAIL_DELIVERY_MAX_ATTEMPTS
    )
    return {
        "status": tracker.status,
        "next_attempt_at": tracker.next_attempt_at,
        "next_allowed_at": tracker.next_allowed_at,
        "is_smtp_down": tracker.status == Status.RETRYING or exhausted,
    }


def deliver_tracker(tracker: EmailVerificationTask) -> bool:
    """Send the mail described by ``tracker``.

    Returns False when the mail is no longer relevant and nothing was
    sent (address verified, replaced or deleted, user gone or inactive).
    SMTP errors propagate to the caller.
    """
    if tracker.kind == EmailVerificationTask.Kind.PASSWORD_RESET:
        return _deliver_password_reset(tracker)
    return _deliver_confirmation(tracker)


def attempt_delivery(tracker_id: int) -> None:
    """Claim the tracker and make one delivery try.

    Does nothing if the tracker is finished, not due yet, or leased by
    another worker. Delivery errors never propagate: they are recorded
    on the tracker (retry or final error).
    """
    now = timezone.now()
    lease = timedelta(seconds=settings.EMAIL_DELIVERY_LEASE_SECONDS)
    claimed = (
        EmailVerificationTask.objects.filter(
            id=tracker_id, status__in=ACTIVE_STATUSES
        )
        .filter(Q(locked_until__isnull=True) | Q(locked_until__lte=now))
        .filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now))
        .update(
            locked_until=now + lease,
            attempts=F("attempts") + 1,
            updated_at=now,
        )
    )
    if not claimed:
        return

    tracker = EmailVerificationTask.objects.get(id=tracker_id)
    try:
        delivered = deliver_tracker(tracker)
    except OSError as exc:
        # smtplib.SMTPException, ConnectionError, TimeoutError and
        # socket.gaierror are all OSError subclasses.
        _record_failure(tracker, exc)
        return

    tracker.status = Status.SENT if delivered else Status.CANCELLED
    tracker.next_attempt_at = None
    tracker.locked_until = None
    tracker.last_error = ""
    if delivered:
        # The pause before the next mail counts from the actual send.
        tracker.next_allowed_at = timezone.now() + timedelta(
            seconds=settings.EMAIL_RESEND_COOLDOWN_SECONDS
        )
    tracker.save(
        update_fields=[
            "status",
            "next_attempt_at",
            "next_allowed_at",
            "locked_until",
            "last_error",
            "updated_at",
        ]
    )


def due_tracker_ids(limit: int = DISPATCH_BATCH_SIZE) -> list[int]:
    """Trackers whose retry is due or whose worker lease has expired."""
    now = timezone.now()
    due = Q(status=Status.RETRYING, next_attempt_at__lte=now) | Q(
        status__in=ACTIVE_STATUSES, locked_until__lte=now
    )
    return list(
        EmailVerificationTask.objects.filter(due)
        .filter(Q(locked_until__isnull=True) | Q(locked_until__lte=now))
        .order_by("updated_at")
        .values_list("id", flat=True)[:limit]
    )


def _record_failure(tracker: EmailVerificationTask, exc: OSError) -> None:
    permanent = is_permanent_error(exc)
    exhausted = tracker.attempts >= settings.EMAIL_DELIVERY_MAX_ATTEMPTS
    final = permanent or exhausted

    tracker.status = Status.ERROR if final else Status.RETRYING
    tracker.next_attempt_at = (
        None
        if final
        else timezone.now()
        + timedelta(seconds=backoff_seconds(tracker.attempts))
    )
    tracker.locked_until = None
    tracker.last_error = type(exc).__name__[:64]
    tracker.save(
        update_fields=[
            "status",
            "next_attempt_at",
            "locked_until",
            "last_error",
            "updated_at",
        ]
    )
    # Only ids and the exception class: never the address, the message
    # text, a key or a token.
    log = logger.error if final else logger.warning
    log(
        "email_delivery.failed",
        extra={
            "tracker_id": tracker.id,
            "attempt": tracker.attempts,
            "error_class": type(exc).__name__,
            "permanent": permanent,
            "final": final,
        },
    )


def _deliver_confirmation(tracker: EmailVerificationTask) -> bool:
    address = EmailAddress.objects.filter(
        user_id=tracker.user_id, email__iexact=tracker.email
    ).first()
    if address is None or address.verified:
        return False
    kinds = EmailVerificationTask.Kind
    signup = tracker.kind == kinds.EMAIL_CONFIRMATION_SIGNUP
    # Built directly (not via EmailAddress.send_confirmation) so that no
    # allauth cooldown set at enqueue time can swallow this send.
    confirmation = EmailConfirmationHMAC(address)
    with deliver_now():
        get_adapter().send_confirmation_mail(None, confirmation, signup)
    return True


def _deliver_password_reset(tracker: EmailVerificationTask) -> bool:
    user = tracker.user
    if user is None or not user.is_active:
        return False
    with deliver_now():
        password_reset_flow.request_password_reset(
            None, tracker.email, [user], None
        )
    return True
