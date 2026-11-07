from __future__ import annotations

import time

from accounts.services.email_delivery import (
    attempt_delivery,
    due_tracker_ids,
)
from django.core.mail import EmailMultiAlternatives

# django-q kills a task after Q_CLUSTER["timeout"] (60 s): stop earlier.
DISPATCH_TIME_BUDGET_SECONDS = 40


def send_email_task(tracker_id: int) -> None:
    """First delivery try, queued together with the tracker."""
    attempt_delivery(tracker_id)


def dispatch_due_emails() -> None:
    """Scheduled every minute: run retries that are due.

    Also picks up trackers whose worker died mid-try (expired lease).
    """
    deadline = time.monotonic() + DISPATCH_TIME_BUDGET_SECONDS
    for tracker_id in due_tracker_ids():
        if time.monotonic() >= deadline:
            return
        attempt_delivery(tracker_id)


def send_plain_email_task(
    to: list[str],
    subject: str,
    body: str,
    from_email: str | None = None,
    subtype: str = "plain",
    alternatives: list[tuple[str, str]] | None = None,
) -> None:
    msg = EmailMultiAlternatives(subject, body, from_email, to)
    msg.content_subtype = subtype
    for content, mimetype in alternatives or []:
        msg.attach_alternative(content, mimetype)
    msg.send(fail_silently=False)
