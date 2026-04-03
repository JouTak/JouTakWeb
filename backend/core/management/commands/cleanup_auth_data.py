from __future__ import annotations

from datetime import timedelta

from allauth.usersessions.models import UserSession
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from ninja_jwt.token_blacklist.models import OutstandingToken

from core.models import UserSessionMeta, UserSessionToken


class Command(BaseCommand):
    help = (
        "Purge stale auth/session metadata according to retention settings "
        "(AUTH_SESSION_RETENTION_DAYS / AUTH_TOKEN_RETENTION_DAYS)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--session-days",
            type=int,
            default=getattr(settings, "AUTH_SESSION_RETENTION_DAYS", 30),
            help="Retention period for session metadata (days)",
        )
        parser.add_argument(
            "--token-days",
            type=int,
            default=getattr(settings, "AUTH_TOKEN_RETENTION_DAYS", 30),
            help="Retention period for token mappings (days)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Calculate how many rows would be removed without deleting",
        )

    @staticmethod
    def _count_or_delete(qs, *, dry_run: bool) -> int:
        if dry_run:
            return qs.count()
        deleted, _ = qs.delete()
        return deleted

    def handle(self, *args, **options):
        session_days = max(int(options["session_days"]), 1)
        token_days = max(int(options["token_days"]), 1)
        dry_run = bool(options.get("dry_run"))

        now = timezone.now()
        session_cutoff = now - timedelta(days=session_days)
        token_cutoff = now - timedelta(days=token_days)

        active_session_keys = Session.objects.values("session_key")

        stale_user_sessions_qs = UserSession.objects.exclude(
            session_key__in=active_session_keys
        ).filter(
            Q(last_seen_at__lt=session_cutoff)
            | Q(created_at__lt=session_cutoff)
        )

        stale_inactive_meta_qs = UserSessionMeta.objects.exclude(
            session_key__in=active_session_keys
        ).filter(
            Q(last_seen__lt=session_cutoff)
            | (Q(last_seen__isnull=True) & Q(first_seen__lt=session_cutoff))
        )
        revoked_meta_qs = UserSessionMeta.objects.filter(
            revoked_at__isnull=False,
            revoked_at__lt=session_cutoff,
        )
        stale_meta_qs = (stale_inactive_meta_qs | revoked_meta_qs).distinct()

        stale_revoked_mappings_qs = UserSessionToken.objects.filter(
            revoked_at__isnull=False,
            revoked_at__lt=token_cutoff,
        )
        stale_orphan_mappings_qs = UserSessionToken.objects.exclude(
            refresh_jti__in=OutstandingToken.objects.values("jti")
        )
        stale_inactive_session_mappings_qs = UserSessionToken.objects.exclude(
            session_key__in=active_session_keys
        ).filter(created_at__lt=token_cutoff)
        stale_mappings_qs = (
            stale_revoked_mappings_qs
            | stale_orphan_mappings_qs
            | stale_inactive_session_mappings_qs
        ).distinct()

        deleted_user_sessions = self._count_or_delete(
            stale_user_sessions_qs,
            dry_run=dry_run,
        )
        deleted_metas = self._count_or_delete(stale_meta_qs, dry_run=dry_run)
        deleted_mappings = self._count_or_delete(
            stale_mappings_qs,
            dry_run=dry_run,
        )

        mode = "dry-run" if dry_run else "apply"
        self.stdout.write(
            "cleanup_auth_data completed "
            f"({mode}): deleted_user_sessions={deleted_user_sessions}, "
            f"deleted_session_metas={deleted_metas}, "
            f"deleted_session_tokens={deleted_mappings}"
        )
