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
import socket
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
ErrorCategory = EmailVerificationTask.ErrorCategory
ACTIVE_STATUSES = (Status.WAITING, Status.RETRYING)
DISPATCH_BATCH_SIZE = 50
# ``last_error`` of a mail given up because its tries ran out.
ATTEMPTS_EXHAUSTED = "AttemptsExhausted"

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


def classify_delivery_error(exc: BaseException) -> str:
    """Map an exception to a structured ``ErrorCategory``."""
    if is_permanent_error(exc):
        return ErrorCategory.MESSAGE_REJECTED
    if isinstance(exc, (smtplib.SMTPException, OSError, socket.timeout)):
        return ErrorCategory.SMTP_UNAVAILABLE
    return ErrorCategory.INTERNAL_ERROR


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
            email__iexact=email,
            kind__in=EmailVerificationTask.CONFIRMATION_KINDS,
        )
        .order_by("-updated_at", "-id")
        .first()
    )


def pending_email_address(user) -> EmailAddress | None:
    """The address that awaits confirmation, if any."""
    return (
        EmailAddress.objects.filter(user=user, verified=False)
        .order_by("-pk")
        .first()
    )


def describe_delivery(tracker: EmailVerificationTask) -> dict[str, object]:
    """Delivery state in the shape of ``EmailDeliveryOut``.

    ``error_category`` is populated whenever the tracker is retrying or in
    final error, and ``None`` for waiting, sent, or cancelled mails.
    ``is_smtp_down`` is true only when ``error_category`` is
    ``smtp_unavailable``.
    """
    has_error = tracker.status in (Status.RETRYING, Status.ERROR)
    category = tracker.error_category if has_error else None
    if has_error and category is None:
        if tracker.last_error == ATTEMPTS_EXHAUSTED:
            category = ErrorCategory.WORKER_INTERRUPTED
        elif (
            tracker.status == Status.ERROR
            and tracker.attempts < settings.EMAIL_DELIVERY_MAX_ATTEMPTS
        ):
            category = ErrorCategory.MESSAGE_REJECTED
        else:
            category = ErrorCategory.SMTP_UNAVAILABLE
    return {
        "email": tracker.email,
        "status": tracker.status,
        "error_category": category,
        "next_attempt_at": tracker.next_attempt_at,
        "next_allowed_at": tracker.next_allowed_at,
        "is_smtp_down": category == ErrorCategory.SMTP_UNAVAILABLE,
    }


def deliver_tracker(tracker: EmailVerificationTask) -> bool:
    """Send the mail described by ``tracker``."""
    if tracker.kind == EmailVerificationTask.Kind.PASSWORD_RESET:
        return _deliver_password_reset(tracker)
    return _deliver_confirmation(tracker)


def attempt_delivery(tracker_id: int) -> None:
    """Claim the tracker and make one delivery try."""
    now = timezone.now()
    max_attempts = settings.EMAIL_DELIVERY_MAX_ATTEMPTS
    claimable = (
        EmailVerificationTask.objects.filter(
            id=tracker_id, status__in=ACTIVE_STATUSES
        )
        .filter(Q(locked_until__isnull=True) | Q(locked_until__lte=now))
        .filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now))
    )
    abandoned = claimable.filter(attempts__gte=max_attempts).update(
        status=Status.ERROR,
        error_category=ErrorCategory.WORKER_INTERRUPTED,
        last_error=ATTEMPTS_EXHAUSTED,
        next_attempt_at=None,
        locked_until=None,
        updated_at=now,
    )
    if abandoned:
        logger.error(
            "email_delivery.abandoned",
            extra={"tracker_id": tracker_id, "attempt": max_attempts},
        )
        return

    lease = timedelta(seconds=settings.EMAIL_DELIVERY_LEASE_SECONDS)
    claimed = claimable.filter(attempts__lt=max_attempts).update(
        locked_until=now + lease,
        attempts=F("attempts") + 1,
        updated_at=now,
    )
    if not claimed:
        return

    tracker = EmailVerificationTask.objects.get(id=tracker_id)
    try:
        delivered = deliver_tracker(tracker)
    except Exception as exc:
        _record_failure(tracker, exc)
        return

    tracker.status = Status.SENT if delivered else Status.CANCELLED
    tracker.error_category = None
    tracker.next_attempt_at = None
    tracker.locked_until = None
    tracker.last_error = ""
    if delivered:
        tracker.next_allowed_at = timezone.now() + timedelta(
            seconds=settings.EMAIL_RESEND_COOLDOWN_SECONDS
        )
    tracker.save(
        update_fields=[
            "status",
            "error_category",
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


def _record_failure(tracker: EmailVerificationTask, exc: Exception) -> None:
    permanent = is_permanent_error(exc)
    exhausted = tracker.attempts >= settings.EMAIL_DELIVERY_MAX_ATTEMPTS
    final = permanent or exhausted
    category = classify_delivery_error(exc)

    tracker.status = Status.ERROR if final else Status.RETRYING
    tracker.error_category = category
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
            "error_category",
            "next_attempt_at",
            "locked_until",
            "last_error",
            "updated_at",
        ]
    )
    log = logger.error if final else logger.warning
    log(
        "email_delivery.failed",
        extra={
            "tracker_id": tracker.id,
            "attempt": tracker.attempts,
            "error_class": type(exc).__name__,
            "error_category": category,
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
    confirmation = EmailConfirmationHMAC(address)
    with deliver_now():
        get_adapter().send_confirmation_mail(None, confirmation, signup)
    return True


def _user_owns_email(user, email: str) -> bool:
    addresses = EmailAddress.objects.filter(user_id=user.pk)
    if addresses.exists():
        return addresses.filter(email__iexact=email).exists()
    return (user.email or "").lower() == email.lower()


def _deliver_password_reset(tracker: EmailVerificationTask) -> bool:
    user = tracker.user
    if user is None or not user.is_active:
        return False
    if not _user_owns_email(user, tracker.email):
        return False
    with deliver_now():
        password_reset_flow.request_password_reset(
            None, tracker.email, [user], None
        )
    return True
