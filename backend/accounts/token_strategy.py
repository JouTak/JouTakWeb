from __future__ import annotations

from allauth.headless.tokens.strategies.sessions import SessionTokenStrategy
from core.models import UserSessionMeta


class RevocableSessionTokenStrategy(SessionTokenStrategy):
    def lookup_session(self, session_token: str):
        if UserSessionMeta.objects.filter(
            session_key=session_token,
            revoked_at__isnull=False,
        ).exists():
            return None
        return super().lookup_session(session_token)
