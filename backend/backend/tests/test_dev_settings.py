from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch


class DevSettingsTests(TestCase):
    def _import_dev_settings(self):
        sys.modules.pop("backend.settings.dev", None)
        sys.modules.pop("backend.settings.base", None)
        sys.modules.pop("backend.settings", None)
        return importlib.import_module("backend.settings.dev")

    def test_uses_sqlite_without_database_url(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            dev = self._import_dev_settings()

        database = dev.DATABASES["default"]
        self.assertEqual(database["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(database["NAME"], dev.BASE_DIR / "db.sqlite3")

    def test_uses_postgres_database_url_for_compose(self) -> None:
        env = {
            "DATABASE_URL": "postgresql://joutak:secret@db:5432/joutak",
        }

        with patch.dict(os.environ, env, clear=True):
            dev = self._import_dev_settings()

        database = dev.DATABASES["default"]
        self.assertEqual(database["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(database["NAME"], "joutak")
        self.assertEqual(database["USER"], "joutak")
        self.assertEqual(database["PASSWORD"], "secret")
        self.assertEqual(database["HOST"], "db")
        self.assertEqual(database["PORT"], 5432)
        self.assertEqual(database["CONN_MAX_AGE"], 0)
        self.assertTrue(database["ATOMIC_REQUESTS"])

    def test_has_safe_http_defaults_for_local_development(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            dev = self._import_dev_settings()

        self.assertTrue(dev.DEBUG)
        self.assertFalse(dev.SECURE_SSL_REDIRECT)
        self.assertEqual(dev.SECURE_HSTS_SECONDS, 0)
        self.assertFalse(dev.SESSION_COOKIE_SECURE)
        self.assertFalse(dev.CSRF_COOKIE_SECURE)
        self.assertFalse(dev.JWT_REFRESH_COOKIE_SECURE)
        self.assertEqual(dev.WEBAUTHN_RP_ID, "localhost")
        self.assertIn("http://localhost:5173", dev.WEBAUTHN_ACCOUNT_ORIGINS)
        self.assertIn("http://admin.localhost", dev.WEBAUTHN_ADMIN_ORIGINS)
        self.assertTrue(dev.MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN)
        self.assertEqual(dev.RATELIMIT_USE_CACHE, "ratelimit")
        self.assertEqual(
            dev.WEBAUTHN_REPLAY_CACHE_ALIAS,
            "webauthn_replay",
        )
        self.assertEqual(
            set(dev.CACHES),
            {"default", "ratelimit", "webauthn_replay"},
        )
        self.assertTrue(
            all(
                cache_config["BACKEND"].endswith("LocMemCache")
                for cache_config in dev.CACHES.values()
            )
        )

    def test_hosts_and_origins_can_be_overridden(self) -> None:
        env = {
            "DJANGO_ALLOWED_HOSTS": "custom.localhost,api.custom.localhost",
            "DJANGO_CSRF_TRUSTED_ORIGINS": "http://custom.localhost",
            "CORS_ALLOW_ALL_ORIGINS": "false",
        }

        with patch.dict(os.environ, env, clear=True):
            dev = self._import_dev_settings()

        self.assertEqual(
            dev.ALLOWED_HOSTS,
            ["custom.localhost", "api.custom.localhost"],
        )
        self.assertEqual(
            dev.CSRF_TRUSTED_ORIGINS,
            ["http://custom.localhost"],
        )
        self.assertFalse(dev.CORS_ALLOW_ALL_ORIGINS)

    def test_media_root_can_live_outside_the_source_checkout(self) -> None:
        with patch.dict(
            os.environ,
            {"MEDIA_ROOT": "/app/media"},
            clear=True,
        ):
            dev = self._import_dev_settings()

        self.assertEqual(dev.MEDIA_ROOT, Path("/app/media"))
