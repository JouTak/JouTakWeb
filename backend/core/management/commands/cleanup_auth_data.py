from __future__ import annotations

from datetime import timedelta

from allauth.usersessions.models import UserSession
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef
from django.db.models.functions import Coalesce
from django.utils import timezone
from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from core.models import UserSessionMeta, UserSessionToken


class Command(BaseCommand):
    help = (
        "Purge expired auth/session audit data according to retention "
        "settings."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--session-days", type=int, default=None)
        parser.add_argument("--token-days", type=int, default=None)

    def handle(self, *args, **options) -> None:
        now = timezone.now()
        session_days = options["session_days"]
        token_days = options["token_days"]
        session_retention_days = session_days or getattr(
            settings, "AUTH_SESSION_RETENTION_DAYS", 30
        )
        token_retention_days = token_days or getattr(
            settings, "AUTH_TOKEN_RETENTION_DAYS", 30
        )

        session_cutoff = now - timedelta(days=session_retention_days)
        token_cutoff = now - timedelta(days=token_retention_days)

        purged_user_sessions = 0
        for user_session in UserSession.objects.iterator():
            if user_session.purge():
                purged_user_sessions += 1

        expired_metas = (
            UserSessionMeta.objects.annotate(
                last_activity=Coalesce("last_seen", "first_seen"),
                has_live_session=Exists(
                    Session.objects.filter(session_key=OuterRef("session_key"))
                ),
            )
            .filter(last_activity__lt=session_cutoff)
            .filter(has_live_session=False)
        )
        revoked_metas = UserSessionMeta.objects.filter(
            revoked_at__lt=session_cutoff
        )
        deleted_expired_metas, _ = expired_metas.delete()
        deleted_revoked_metas, _ = revoked_metas.delete()

        expired_outstanding = OutstandingToken.objects.filter(
            expires_at__lt=token_cutoff
        )
        deleted_blacklisted, _ = BlacklistedToken.objects.filter(
            token__expires_at__lt=token_cutoff
        ).delete()
        deleted_outstanding, _ = expired_outstanding.delete()

        stale_active_token_mappings = (
            UserSessionToken.objects.filter(revoked_at__isnull=True)
            .annotate(
                has_outstanding=Exists(
                    OutstandingToken.objects.filter(jti=OuterRef("refresh_jti"))
                ),
                outstanding_expired=Exists(
                    OutstandingToken.objects.filter(
                        jti=OuterRef("refresh_jti"), expires_at__lt=now
                    )
                ),
                outstanding_blacklisted=Exists(
                    BlacklistedToken.objects.filter(
                        token__jti=OuterRef("refresh_jti")
                    )
                ),
            )
            .filter(
                has_outstanding=False,
                outstanding_expired=False,
                outstanding_blacklisted=False,
            )
        )
        deleted_stale_active_mappings, _ = stale_active_token_mappings.delete()
        deleted_revoked_mappings, _ = UserSessionToken.objects.filter(
            revoked_at__lt=token_cutoff
        ).delete()
        deleted_expired_mappings, _ = UserSessionToken.objects.filter(
            revoked_at__isnull=True,
        ).annotate(
            outstanding_expired=Exists(
                OutstandingToken.objects.filter(
                    jti=OuterRef("refresh_jti"), expires_at__lt=now
                )
            ),
            outstanding_blacklisted=Exists(
                BlacklistedToken.objects.filter(
                    token__jti=OuterRef("refresh_jti")
                )
            ),
        ).filter(
            outstanding_expired=True,
        ).delete()
        deleted_blacklisted_mappings, _ = UserSessionToken.objects.filter(
            revoked_at__isnull=True,
        ).annotate(
            outstanding_blacklisted=Exists(
                BlacklistedToken.objects.filter(
                    token__jti=OuterRef("refresh_jti")
                )
            )
        ).filter(outstanding_blacklisted=True).delete()

        self.stdout.write(
            self.style.SUCCESS(
                "cleanup_auth_data completed: "
                f"purged_user_sessions={purged_user_sessions}, "
                f"deleted_expired_metas={deleted_expired_metas}, "
                f"deleted_revoked_metas={deleted_revoked_metas}, "
                f"deleted_blacklisted={deleted_blacklisted}, "
                f"deleted_outstanding={deleted_outstanding}, "
                "deleted_stale_active_mappings="
                f"{deleted_stale_active_mappings}, "
                f"deleted_revoked_mappings={deleted_revoked_mappings}, "
                f"deleted_expired_mappings={deleted_expired_mappings}, "
                f"deleted_blacklisted_mappings={deleted_blacklisted_mappings}"
            )
        )
