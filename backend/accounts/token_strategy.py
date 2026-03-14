from __future__ import annotations

from allauth.headless.tokens.strategies.sessions import SessionTokenStrategy
from core.models import UserSessionMeta
from django.db.models import Q


class RevocableSessionTokenStrategy(SessionTokenStrategy):
    def lookup_session(self, session_token: str):
        if UserSessionMeta.objects.filter(
            Q(session_key=session_token) | Q(session_token=session_token),
            revoked_at__isnull=False,
        ).exists():
            return None
        return super().lookup_session(session_token)
