from __future__ import annotations

from datetime import timedelta

from allauth.usersessions.models import UserSession
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from core.models import UserSessionMeta, UserSessionToken


class Command(BaseCommand):
    """Purge expired auth/session audit data.

    Retention is driven by two knobs:

    * ``AUTH_SESSION_RETENTION_DAYS`` — how long we keep
      ``UserSessionMeta`` rows after the underlying Django session went
      away or was explicitly revoked.
    * ``AUTH_TOKEN_RETENTION_DAYS`` — how long we keep JWT bookkeeping
      (``OutstandingToken`` / ``BlacklistedToken`` / ``UserSessionToken``)
      after the refresh token expired or was revoked.

    The command is idempotent and safe to run repeatedly from cron.
    """

    help = (
        "Purge expired auth/session audit data according to retention "
        "settings."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--session-days", type=int, default=None)
        parser.add_argument("--token-days", type=int, default=None)

    def handle(self, *args, **options) -> None:
        now = timezone.now()
        session_retention_days = options["session_days"] or getattr(
            settings, "AUTH_SESSION_RETENTION_DAYS", 30
        )
        token_retention_days = options["token_days"] or getattr(
            settings, "AUTH_TOKEN_RETENTION_DAYS", 30
        )

        session_cutoff = now - timedelta(days=session_retention_days)
        token_cutoff = now - timedelta(days=token_retention_days)

        purged_user_sessions = self._purge_allauth_sessions()
        deleted_expired_metas, deleted_revoked_metas = self._purge_metas(
            session_cutoff
        )
        deleted_blacklisted, deleted_outstanding = self._purge_jwt_records(
            token_cutoff
        )
        deleted_token_mappings = self._purge_token_mappings(
            now=now, token_cutoff=token_cutoff
        )

        self.stdout.write(
            self.style.SUCCESS(
                "cleanup_auth_data completed: "
                f"purged_user_sessions={purged_user_sessions}, "
                f"deleted_expired_metas={deleted_expired_metas}, "
                f"deleted_revoked_metas={deleted_revoked_metas}, "
                f"deleted_blacklisted={deleted_blacklisted}, "
                f"deleted_outstanding={deleted_outstanding}, "
                f"deleted_token_mappings={deleted_token_mappings}"
            )
        )

    # ------------------------------------------------------------------
    # Step 1: allauth UserSession objects.
    #
    # ``UserSession.purge()`` is an instance method on allauth's model
    # and we have no bulk equivalent — the per-row call is inherent to
    # allauth's API, not a code smell we can fix here. We iterate with
    # ``iterator()`` to avoid loading everything at once.
    # ------------------------------------------------------------------
    @staticmethod
    def _purge_allauth_sessions() -> int:
        purged = 0
        for user_session in UserSession.objects.iterator():
            if user_session.purge():
                purged += 1
        return purged

    # ------------------------------------------------------------------
    # Step 2: UserSessionMeta — drop rows whose Django session is gone
    # and were last seen before the retention cutoff, plus rows
    # explicitly revoked long enough ago.
    # ------------------------------------------------------------------
    @staticmethod
    def _purge_metas(session_cutoff) -> tuple[int, int]:
        expired_qs = (
            UserSessionMeta.objects.annotate(
                last_activity=Coalesce("last_seen", "first_seen"),
                has_live_session=Exists(
                    Session.objects.filter(session_key=OuterRef("session_key"))
                ),
            )
            .filter(has_live_session=False)
            .filter(last_activity__lt=session_cutoff)
        )
        revoked_qs = UserSessionMeta.objects.filter(
            revoked_at__lt=session_cutoff
        )
        deleted_expired, _ = expired_qs.delete()
        deleted_revoked, _ = revoked_qs.delete()
        return deleted_expired, deleted_revoked

    # ------------------------------------------------------------------
    # Step 3: raw JWT bookkeeping. Blacklist first (FK on outstanding),
    # then outstanding. ``expires_at`` lives on ``OutstandingToken`` and
    # is always populated by ninja_jwt, so a direct filter is enough.
    # ------------------------------------------------------------------
    @staticmethod
    def _purge_jwt_records(token_cutoff) -> tuple[int, int]:
        deleted_blacklisted, _ = BlacklistedToken.objects.filter(
            token__expires_at__lt=token_cutoff
        ).delete()
        deleted_outstanding, _ = OutstandingToken.objects.filter(
            expires_at__lt=token_cutoff
        ).delete()
        return deleted_blacklisted, deleted_outstanding

    # ------------------------------------------------------------------
    # Step 4: UserSessionToken mappings.
    #
    # After step 3 ``OutstandingToken`` only contains *unexpired* rows,
    # which means a mapping is stale iff any of the following holds:
    #
    #   * ``revoked_at`` is older than the retention cutoff,
    #   * the row's own ``expires_at`` is in the past (populated on new
    #     mappings since migration 0005),
    #   * there is no matching ``OutstandingToken`` AND no
    #     ``BlacklistedToken`` — i.e. the JWT bookkeeping has already
    #     been pruned out from under us in step 3.
    #
    # All three predicates fold into a single ``.filter(...).delete()``
    # call, which collapses the three near-duplicate EXISTS-delete
    # blocks the old implementation had.
    # ------------------------------------------------------------------
    @staticmethod
    def _purge_token_mappings(*, now, token_cutoff) -> int:
        has_outstanding = Exists(
            OutstandingToken.objects.filter(jti=OuterRef("refresh_jti"))
        )
        has_blacklisted = Exists(
            BlacklistedToken.objects.filter(token__jti=OuterRef("refresh_jti"))
        )
        stale = UserSessionToken.objects.annotate(
            _has_outstanding=has_outstanding,
            _has_blacklisted=has_blacklisted,
        ).filter(
            Q(revoked_at__lt=token_cutoff)
            | Q(expires_at__lt=now)
            | Q(_has_outstanding=False, _has_blacklisted=False)
        )
        deleted, _ = stale.delete()
        return deleted
