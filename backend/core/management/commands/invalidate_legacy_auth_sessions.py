from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from allauth.usersessions.models import UserSession
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Exists, OuterRef, QuerySet
from django.utils import timezone
from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from core.models import UserSessionMeta, UserSessionToken

REVOCATION_REASON = "cookie_name_cutover"
BLACKLIST_BATCH_SIZE = 1000


@dataclass(frozen=True, slots=True)
class InvalidationCounts:
    django_sessions: int
    allauth_user_sessions: int
    active_session_meta: int
    active_session_tokens: int
    unblacklisted_refresh_tokens: int

    def render(self) -> str:
        return (
            f"django_sessions={self.django_sessions}, "
            f"allauth_user_sessions={self.allauth_user_sessions}, "
            f"active_session_meta={self.active_session_meta}, "
            f"active_session_tokens={self.active_session_tokens}, "
            "unblacklisted_refresh_tokens="
            f"{self.unblacklisted_refresh_tokens}"
        )


class Command(BaseCommand):
    """Invalidate sessions issued before the host-only cookie cutover.

    The deployment must stop or drain authentication writes while applying
    this command. Django's session rows do not record the cookie name that
    created them, so the cutover intentionally invalidates every existing
    Django session, including anonymous sessions.
    """

    help = (
        "Invalidate legacy Django, allauth, project session, and refresh "
        "token state before changing the production session cookie name. "
        "Runs as a dry-run unless --apply is provided."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--apply",
            action="store_true",
            help=(
                "Apply the invalidation. Authentication writes must be "
                "stopped or drained first."
            ),
        )

    def handle(self, *args, **options) -> None:
        if options["apply"]:
            counts = self._apply_invalidation()
            mode = "applied"
            styled_output = self.style.SUCCESS
        else:
            counts = self._collect_counts()
            mode = "dry-run"
            styled_output = self.style.WARNING

        self.stdout.write(
            styled_output(
                f"invalidate_legacy_auth_sessions {mode}: {counts.render()}"
            )
        )

    @staticmethod
    def _unblacklisted_refresh_tokens() -> QuerySet[OutstandingToken]:
        has_blacklist_entry = Exists(
            BlacklistedToken.objects.filter(token_id=OuterRef("pk"))
        )
        return OutstandingToken.objects.annotate(
            _has_blacklist_entry=has_blacklist_entry
        ).filter(_has_blacklist_entry=False)

    @classmethod
    def _collect_counts(cls) -> InvalidationCounts:
        return InvalidationCounts(
            django_sessions=Session.objects.count(),
            allauth_user_sessions=UserSession.objects.count(),
            active_session_meta=UserSessionMeta.objects.filter(
                revoked_at__isnull=True
            ).count(),
            active_session_tokens=UserSessionToken.objects.filter(
                revoked_at__isnull=True
            ).count(),
            unblacklisted_refresh_tokens=(
                cls._unblacklisted_refresh_tokens().count()
            ),
        )

    @classmethod
    @transaction.atomic
    def _apply_invalidation(cls) -> InvalidationCounts:
        counts = cls._collect_counts()
        now = timezone.now()

        Session.objects.all().delete()
        UserSession.objects.all().delete()
        UserSessionMeta.objects.filter(revoked_at__isnull=True).update(
            revoked_at=now,
            revoked_reason=REVOCATION_REASON,
        )
        UserSessionToken.objects.filter(revoked_at__isnull=True).update(
            revoked_at=now
        )
        cls._blacklist_outstanding_refresh_tokens(now=now)
        return counts

    @classmethod
    def _blacklist_outstanding_refresh_tokens(
        cls,
        *,
        now: datetime,
    ) -> None:
        last_pk = 0
        while True:
            token_ids = list(
                cls._unblacklisted_refresh_tokens()
                .filter(pk__gt=last_pk)
                .order_by("pk")
                .values_list("pk", flat=True)[:BLACKLIST_BATCH_SIZE]
            )
            if not token_ids:
                return
            BlacklistedToken.objects.bulk_create(
                [
                    BlacklistedToken(token_id=token_id, blacklisted_at=now)
                    for token_id in token_ids
                ],
                ignore_conflicts=True,
            )
            last_pk = token_ids[-1]
