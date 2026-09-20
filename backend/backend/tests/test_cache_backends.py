from __future__ import annotations

from unittest.mock import patch

from django.core.cache import caches
from django.core.management import call_command
from django.test import RequestFactory, TransactionTestCase, override_settings
from django_ratelimit.core import is_ratelimited

from backend.cache_backends import (
    SecurityCacheCapacityError,
    SecurityCacheWriteError,
)

RATE_TABLE = "test_fail_closed_ratelimit_cache"
REPLAY_TABLE = "test_fail_closed_webauthn_replay_cache"
DEFAULT_TABLE = "test_fail_closed_default_cache"
FAIL_CLOSED_CACHES = {
    "default": {
        "BACKEND": "backend.cache_backends.FailClosedDatabaseCache",
        "LOCATION": DEFAULT_TABLE,
        "OPTIONS": {"MAX_ENTRIES": 2},
    },
    "ratelimit": {
        "BACKEND": "backend.cache_backends.FailClosedDatabaseCache",
        "LOCATION": RATE_TABLE,
        "OPTIONS": {"MAX_ENTRIES": 2},
    },
    "webauthn_replay": {
        "BACKEND": "backend.cache_backends.FailClosedDatabaseCache",
        "LOCATION": REPLAY_TABLE,
        "OPTIONS": {"MAX_ENTRIES": 2},
    },
}


@override_settings(
    CACHES=FAIL_CLOSED_CACHES,
    RATELIMIT_USE_CACHE="ratelimit",
    RATELIMIT_FAIL_OPEN=False,
    WEBAUTHN_REPLAY_CACHE_ALIAS="webauthn_replay",
)
class FailClosedDatabaseCacheTests(TransactionTestCase):
    def setUp(self) -> None:
        for table in (DEFAULT_TABLE, RATE_TABLE, REPLAY_TABLE):
            call_command("createcachetable", table, verbosity=0)
        for backend in caches.all():
            backend.clear()
        # A test deliberately lowers this value to exercise the race-overflow
        # path. Cache instances are connection-local and survive cache.clear().
        caches["ratelimit"]._max_entries = 2
        caches["webauthn_replay"]._max_entries = 2
        caches["default"]._max_entries = 2

    def test_capacity_preserves_live_keys_and_raises_for_new_key(self) -> None:
        backend = caches["ratelimit"]
        self.assertTrue(backend.set("first", 1, timeout=60))
        self.assertTrue(backend.set("second", 2, timeout=60))

        with self.assertRaises(SecurityCacheCapacityError):
            backend.add("third", 3, timeout=60)

        self.assertEqual(backend.get("first"), 1)
        self.assertEqual(backend.get("second"), 2)
        self.assertTrue(backend.set("first", 10, timeout=60))
        self.assertEqual(backend.incr("first"), 11)
        self.assertFalse(backend.add("first", 99, timeout=60))

    def test_cull_never_removes_live_keys_after_racing_overflow(self) -> None:
        backend = caches["ratelimit"]
        backend.set("first", 1, timeout=60)
        backend.set("second", 2, timeout=60)

        # Simulate concurrent inserts having exceeded the configured budget.
        # Updating an existing key invokes DatabaseCache._base_set(), whose
        # normal implementation would cull a live row when num > max.
        backend._max_entries = 1
        self.assertTrue(backend.set("first", 10, timeout=60))

        self.assertEqual(backend.get("first"), 10)
        self.assertEqual(backend.get("second"), 2)
        with self.assertRaises(SecurityCacheCapacityError):
            backend.set("third", 3, timeout=60)

    def test_expired_row_frees_capacity_for_new_security_state(self) -> None:
        backend = caches["ratelimit"]
        backend.set("expired", 1, timeout=-1)
        backend.set("live", 2, timeout=60)

        self.assertTrue(backend.add("replacement", 3, timeout=60))

        self.assertIsNone(backend.get("expired"))
        self.assertEqual(backend.get("live"), 2)
        self.assertEqual(backend.get("replacement"), 3)

    def test_capacity_error_propagates_through_ratelimit_precheck(
        self,
    ) -> None:
        backend = caches["ratelimit"]
        backend.set("occupied-1", 1, timeout=60)
        backend.set("occupied-2", 2, timeout=60)
        request = RequestFactory().post(
            "/admin/mfa-verify/",
            REMOTE_ADDR="203.0.113.10",
        )

        with self.assertRaises(SecurityCacheCapacityError):
            is_ratelimited(
                request,
                group="admin.mfa.capacity-test",
                key=lambda _group, _request: "new-identity",
                rate="1/m",
                increment=False,
            )

    def test_replay_capacity_is_isolated_from_rate_counters(self) -> None:
        replay = caches["webauthn_replay"]
        self.assertTrue(replay.add("claim-1", True, timeout=60))
        # A repeated nonce remains the normal add collision that middleware
        # classifies as replay, not a cache-write outage.
        self.assertFalse(replay.add("claim-1", True, timeout=60))
        replay.set("claim-2", True, timeout=60)
        with self.assertRaises(SecurityCacheCapacityError):
            replay.add("claim-3", True, timeout=60)

        ratelimit = caches["ratelimit"]
        self.assertTrue(ratelimit.add("counter", 1, timeout=60))
        self.assertEqual(ratelimit.get("counter"), 1)

    def test_default_allauth_security_state_is_fail_closed_at_capacity(
        self,
    ) -> None:
        backend = caches["default"]
        backend.set("allauth-rate-history", [1], timeout=60)
        backend.set("allauth-totp-used-code", "123456", timeout=60)

        backend._max_entries = 1
        backend.set("allauth-rate-history", [1, 2], timeout=60)

        self.assertEqual(backend.get("allauth-rate-history"), [1, 2])
        self.assertEqual(backend.get("allauth-totp-used-code"), "123456")
        with self.assertRaises(SecurityCacheCapacityError):
            backend.add("new-allauth-security-key", [], timeout=60)

    def test_silent_database_write_failures_raise_unless_add_exists(
        self,
    ) -> None:
        backend = caches["default"]

        with patch.object(backend, "_base_set", return_value=False):
            with self.assertRaises(SecurityCacheWriteError):
                backend.set("missing-set", "value", timeout=60)
            with self.assertRaises(SecurityCacheWriteError):
                backend.add("missing-add", "value", timeout=60)

        backend.set("existing-add", "original", timeout=60)
        with patch.object(backend, "_base_set", return_value=False):
            self.assertFalse(
                backend.add("existing-add", "replacement", timeout=60)
            )
        self.assertEqual(backend.get("existing-add"), "original")
