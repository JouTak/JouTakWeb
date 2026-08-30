from __future__ import annotations

from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.db import DatabaseCache
from django.db import connections, router, transaction
from django.utils import timezone


class SecurityCacheCapacityError(RuntimeError):
    """A security cache is full of unexpired entries."""


class SecurityCacheWriteError(RuntimeError):
    """A security cache write failed without preserving equivalent state."""


class FailClosedDatabaseCache(DatabaseCache):
    """Database cache that never evicts unexpired security state.

    Django's ``DatabaseCache`` culls live rows after ``MAX_ENTRIES`` is
    exceeded.  That is a useful availability trade-off for ordinary cached
    data, but it can silently reset a rate-limit counter or a WebAuthn replay
    claim.  This backend removes expired rows only.  Once the live-row budget
    is full, updates to existing keys continue to work while insertion of a
    new key raises ``SecurityCacheCapacityError`` so security callers fail
    closed. Returning ``False`` is insufficient: django-ratelimit interprets
    an absent key as count zero during an ``increment=False`` precheck.

    The capacity check deliberately does not take a table-wide lock.  Racing
    inserts may transiently exceed the configured budget, but they never
    delete live state.  Subsequent new keys are rejected until rows expire.
    """

    def add(
        self,
        key,
        value,
        timeout=DEFAULT_TIMEOUT,
        version=None,
    ):
        logical_key = key
        physical_key = self.make_and_validate_key(key, version=version)
        if not self._can_store(physical_key):
            raise SecurityCacheCapacityError(
                "Security cache capacity is exhausted."
            )
        stored = self._base_set("add", physical_key, value, timeout)
        if stored:
            return True

        # DatabaseCache returns False both for the normal "already exists"
        # add result and for a swallowed DatabaseError. Distinguish them so a
        # failed security-state write cannot look like a harmless collision.
        missing = object()
        try:
            existing = self.get(logical_key, missing, version=version)
        except Exception as exc:
            raise SecurityCacheWriteError(
                "Security cache add could not be verified."
            ) from exc
        if existing is missing:
            raise SecurityCacheWriteError("Security cache add failed.")
        return False

    def set(
        self,
        key,
        value,
        timeout=DEFAULT_TIMEOUT,
        version=None,
    ):
        key = self.make_and_validate_key(key, version=version)
        if not self._can_store(key):
            raise SecurityCacheCapacityError(
                "Security cache capacity is exhausted."
            )
        stored = self._base_set("set", key, value, timeout)
        if not stored:
            raise SecurityCacheWriteError("Security cache set failed.")
        return True

    def _can_store(self, key: str) -> bool:
        """Allow an update, or reserve capacity for one new physical row."""
        db = router.db_for_write(self.cache_model_class)
        connection = connections[db]
        quote_name = connection.ops.quote_name
        table = quote_name(self._table)
        key_column = quote_name("cache_key")
        expires_column = quote_name("expires")
        now = timezone.now().replace(microsecond=0)
        adapted_now = connection.ops.adapt_datetimefield_value(now)

        with transaction.atomic(using=db), connection.cursor() as cursor:
            # Identifiers come from Django's quoted, fixed cache-table config;
            # the only request-derived value remains a bound parameter.
            cursor.execute(
                f"SELECT {key_column} FROM {table} "  # nosec B608
                f"WHERE {key_column} = %s",
                [key],
            )
            if cursor.fetchone() is not None:
                # Updating (or replacing an expired value at the same key)
                # cannot consume another row, so it remains available even
                # when the cache is full.
                return True

            cursor.execute(
                f"DELETE FROM {table} "  # nosec B608
                f"WHERE {expires_column} < %s",
                [adapted_now],
            )
            cursor.execute(
                f"SELECT COUNT(*) FROM {table}"  # nosec B608
            )
            return cursor.fetchone()[0] < self._max_entries

    def _cull(self, db, cursor, now, num) -> None:
        """Purge expired rows without ever deleting a live cache entry."""
        del num
        connection = connections[db]
        table = connection.ops.quote_name(self._table)
        expires_column = connection.ops.quote_name("expires")
        cursor.execute(
            f"DELETE FROM {table} "  # nosec B608
            f"WHERE {expires_column} < %s",
            [connection.ops.adapt_datetimefield_value(now)],
        )


__all__ = [
    "FailClosedDatabaseCache",
    "SecurityCacheCapacityError",
    "SecurityCacheWriteError",
]
