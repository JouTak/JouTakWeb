from __future__ import annotations

from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from allauth.usersessions.models import UserSession
from core.models import UserSessionMeta, UserSessionToken
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from ninja_jwt.token_blacklist.models import OutstandingToken

User = get_user_model()


class ManagementCommandsTests(TestCase):
    @override_settings(FRONTEND_BASE_URL="https://fallback.example")
    def test_sync_site_uses_configured_domain_and_name(self) -> None:
        out = StringIO()
        with patch.dict(
            "os.environ",
            {
                "DJANGO_SITE_DOMAIN": "https://joutak.ru",
                "DJANGO_SITE_NAME": "JouTak",
            },
            clear=False,
        ):
            call_command("sync_site", stdout=out)

        site = Site.objects.get(id=settings.SITE_ID)
        self.assertEqual(site.domain, "joutak.ru")
        self.assertEqual(site.name, "JouTak")
        self.assertIn("Updated Site", out.getvalue())

    def test_cleanup_auth_data_removes_stale_records(self) -> None:
        user = User.objects.create_user(
            username="cleanup_user",
            email="cleanup_user@example.com",
            password="StrongPass123!",
        )
        now = timezone.now()
        stale_at = now - timedelta(days=3)
        future = now + timedelta(days=3)

        Session.objects.create(
            session_key="active_session",
            session_data="",
            expire_date=future,
        )
        active_user_session = UserSession.objects.create(
            user=user,
            session_key="active_session",
            ip="127.0.0.1",
            user_agent="active",
            data={},
        )
        UserSession.objects.filter(pk=active_user_session.pk).update(
            created_at=stale_at,
            last_seen_at=stale_at,
        )

        stale_user_session = UserSession.objects.create(
            user=user,
            session_key="stale_session",
            ip="127.0.0.2",
            user_agent="stale",
            data={},
        )
        UserSession.objects.filter(pk=stale_user_session.pk).update(
            created_at=stale_at,
            last_seen_at=stale_at,
        )

        active_meta = UserSessionMeta.objects.create(
            user=user,
            session_key="active_session",
            first_seen=stale_at,
            last_seen=stale_at,
        )
        stale_meta = UserSessionMeta.objects.create(
            user=user,
            session_key="stale_session",
            first_seen=stale_at,
            last_seen=stale_at,
        )

        active_mapping = UserSessionToken.objects.create(
            user=user,
            session_key="active_session",
            refresh_jti="active-jti",
        )
        UserSessionToken.objects.filter(pk=active_mapping.pk).update(
            created_at=stale_at
        )
        OutstandingToken.objects.create(
            user=user,
            jti="active-jti",
            token="active-token",
            created_at=stale_at,
            expires_at=future,
        )

        stale_mapping = UserSessionToken.objects.create(
            user=user,
            session_key="stale_session",
            refresh_jti="stale-jti",
        )
        UserSessionToken.objects.filter(pk=stale_mapping.pk).update(
            created_at=stale_at
        )

        call_command("cleanup_auth_data", session_days=1, token_days=1)

        self.assertTrue(UserSession.objects.filter(pk=active_user_session.pk).exists())
        self.assertFalse(UserSession.objects.filter(pk=stale_user_session.pk).exists())

        self.assertTrue(UserSessionMeta.objects.filter(pk=active_meta.pk).exists())
        self.assertFalse(UserSessionMeta.objects.filter(pk=stale_meta.pk).exists())

        self.assertTrue(UserSessionToken.objects.filter(pk=active_mapping.pk).exists())
        self.assertFalse(UserSessionToken.objects.filter(pk=stale_mapping.pk).exists())
