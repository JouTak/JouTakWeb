from __future__ import annotations

from allauth.headless.tokens.strategies.sessions import SessionTokenStrategy
from core.models import UserSessionMeta, session_token_digest
from django.db.models import Q


class RevocableSessionTokenStrategy(SessionTokenStrategy):
    def lookup_session(self, session_token: str):
        token_digest = session_token_digest(session_token)
        if UserSessionMeta.objects.filter(
            Q(session_key=session_token)
            | Q(session_token_digest=token_digest),
            revoked_at__isnull=False,
        ).exists():
            return None
        return super().lookup_session(session_token)
