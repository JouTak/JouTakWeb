from __future__ import annotations

import hashlib
from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings

from backend.ratelimiting import _rate_limit_identity


@override_settings(
    ACCOUNT_TRUST_PROXY_HEADERS=True,
    ACCOUNT_TRUSTED_PROXY_CIDRS=("10.0.0.0/8",),
)
class RatelimitingTests(SimpleTestCase):
    def test_uses_trusted_client_ip_behind_proxy(self):
        request = SimpleNamespace(
            META={
                "REMOTE_ADDR": "10.0.0.5",
                "HTTP_X_REAL_IP": "203.0.113.9",
                "HTTP_X_FORWARDED_FOR": "203.0.113.9, 10.0.0.5",
            }
        )

        self.assertEqual(
            _rate_limit_identity("auth.login", request),
            "ip:203.0.113.9",
        )

    def test_prefers_session_token_for_session_scoped_routes(self):
        request = SimpleNamespace(
            META={
                "REMOTE_ADDR": "10.0.0.5",
                "HTTP_X_REAL_IP": "203.0.113.9",
                "HTTP_X_SESSION_TOKEN": "session-token",
            },
            user=SimpleNamespace(is_authenticated=True, pk=42),
        )

        self.assertEqual(
            _rate_limit_identity("auth.refresh", request),
            "session:"
            + hashlib.sha256("session-token".encode("utf-8")).hexdigest(),
        )
