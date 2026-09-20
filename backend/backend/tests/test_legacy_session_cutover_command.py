from __future__ import annotations

from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from allauth.usersessions.models import UserSession
from core.models import UserSessionMeta, UserSessionToken
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken

User = get_user_model()


class InvalidateLegacyAuthSessionsCommandTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="cookie-cutover-user",
            email="cutover@example.test",
            password="StrongPass123!",
        )
        session_store = SessionStore()
        session_store["marker"] = "legacy-session-payload"
        session_store.save()
        self.session_key = session_store.session_key
        UserSession.objects.create(
            user=self.user,
            session_key=self.session_key,
            ip="127.0.0.1",
            user_agent="legacy-user-agent-sentinel",
        )

        self.active_meta = UserSessionMeta.objects.create(
            user=self.user,
            session_key=self.session_key,
        )
        self.already_revoked_meta = UserSessionMeta.objects.create(
            user=self.user,
            session_key="already-revoked-session",
            revoked_at=timezone.now(),
            revoked_reason="manual",
        )

        self.mapped_outstanding = self._create_outstanding(
            "mapped-refresh-jti-sentinel"
        )
        self.active_mapping = UserSessionToken.objects.create(
            user=self.user,
            session_key=self.session_key,
            refresh_jti=self.mapped_outstanding.jti,
        )
        self.orphan_outstanding = self._create_outstanding(
            "orphan-refresh-jti-sentinel"
        )
        already_blacklisted = self._create_outstanding(
            "blacklisted-refresh-jti-sentinel"
        )
        BlacklistedToken.objects.create(token=already_blacklisted)
        self.already_revoked_mapping = UserSessionToken.objects.create(
            user=self.user,
            session_key="already-revoked-session",
            refresh_jti=already_blacklisted.jti,
            revoked_at=timezone.now(),
        )

    def _create_outstanding(self, jti: str) -> OutstandingToken:
        return OutstandingToken.objects.create(
            user=self.user,
            jti=jti,
            token=f"raw-token-{jti}",
            expires_at=timezone.now() + timedelta(days=1),
        )

    def test_defaults_to_aggregate_only_dry_run(self) -> None:
        stdout = StringIO()

        call_command("invalidate_legacy_auth_sessions", stdout=stdout)

        self.assertTrue(
            Session.objects.filter(session_key=self.session_key).exists()
        )
        self.assertTrue(
            UserSession.objects.filter(session_key=self.session_key).exists()
        )
        self.active_meta.refresh_from_db()
        self.active_mapping.refresh_from_db()
        self.assertIsNone(self.active_meta.revoked_at)
        self.assertIsNone(self.active_mapping.revoked_at)
        self.assertEqual(BlacklistedToken.objects.count(), 1)

        output = stdout.getvalue()
        self.assertIn("invalidate_legacy_auth_sessions dry-run", output)
        self.assertIn("django_sessions=1", output)
        self.assertIn("allauth_user_sessions=1", output)
        self.assertIn("active_session_meta=1", output)
        self.assertIn("active_session_tokens=1", output)
        self.assertIn("unblacklisted_refresh_tokens=2", output)
        for sensitive_value in (
            self.user.email,
            self.session_key,
            self.mapped_outstanding.jti,
            self.orphan_outstanding.jti,
            "legacy-user-agent-sentinel",
        ):
            self.assertNotIn(sensitive_value, output)

    def test_apply_invalidates_every_layer_and_is_idempotent(self) -> None:
        original_meta_revoked_at = self.already_revoked_meta.revoked_at
        original_mapping_revoked_at = self.already_revoked_mapping.revoked_at
        stdout = StringIO()

        call_command(
            "invalidate_legacy_auth_sessions", "--apply", stdout=stdout
        )

        self.assertFalse(Session.objects.exists())
        self.assertFalse(UserSession.objects.exists())
        self.active_meta.refresh_from_db()
        self.active_mapping.refresh_from_db()
        self.already_revoked_meta.refresh_from_db()
        self.already_revoked_mapping.refresh_from_db()
        self.assertIsNotNone(self.active_meta.revoked_at)
        self.assertEqual(
            self.active_meta.revoked_reason,
            "cookie_name_cutover",
        )
        self.assertIsNotNone(self.active_mapping.revoked_at)
        self.assertEqual(
            self.already_revoked_meta.revoked_at,
            original_meta_revoked_at,
        )
        self.assertEqual(self.already_revoked_meta.revoked_reason, "manual")
        self.assertEqual(
            self.already_revoked_mapping.revoked_at,
            original_mapping_revoked_at,
        )
        self.assertEqual(
            BlacklistedToken.objects.count(),
            OutstandingToken.objects.count(),
        )
        self.assertIn(
            "invalidate_legacy_auth_sessions applied",
            stdout.getvalue(),
        )

        first_meta_revoked_at = self.active_meta.revoked_at
        first_mapping_revoked_at = self.active_mapping.revoked_at
        second_stdout = StringIO()
        call_command(
            "invalidate_legacy_auth_sessions",
            "--apply",
            stdout=second_stdout,
        )

        self.active_meta.refresh_from_db()
        self.active_mapping.refresh_from_db()
        self.assertEqual(self.active_meta.revoked_at, first_meta_revoked_at)
        self.assertEqual(
            self.active_mapping.revoked_at,
            first_mapping_revoked_at,
        )
        self.assertIn("django_sessions=0", second_stdout.getvalue())
        self.assertIn("allauth_user_sessions=0", second_stdout.getvalue())
        self.assertIn("active_session_meta=0", second_stdout.getvalue())
        self.assertIn("active_session_tokens=0", second_stdout.getvalue())
        self.assertIn(
            "unblacklisted_refresh_tokens=0",
            second_stdout.getvalue(),
        )

    def test_apply_rolls_back_all_layers_when_blacklisting_fails(self) -> None:
        with (
            patch(
                "core.management.commands.invalidate_legacy_auth_sessions."
                "BlacklistedToken.objects.bulk_create",
                side_effect=RuntimeError("database write failed"),
            ),
            self.assertRaisesMessage(RuntimeError, "database write failed"),
        ):
            call_command("invalidate_legacy_auth_sessions", "--apply")

        self.assertTrue(
            Session.objects.filter(session_key=self.session_key).exists()
        )
        self.assertTrue(
            UserSession.objects.filter(session_key=self.session_key).exists()
        )
        self.active_meta.refresh_from_db()
        self.active_mapping.refresh_from_db()
        self.assertIsNone(self.active_meta.revoked_at)
        self.assertIsNone(self.active_mapping.revoked_at)
        self.assertEqual(BlacklistedToken.objects.count(), 1)
