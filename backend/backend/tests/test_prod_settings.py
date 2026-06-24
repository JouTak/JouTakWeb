from __future__ import annotations

import importlib
import os
import sys
from unittest import TestCase
from unittest.mock import patch


class ProdSettingsFrontendBaseUrlTests(TestCase):
    VALID_SECRET_KEY = (
        "test-secret-key-change-me-please-very-long-1234567890"
    )

    def _import_prod_settings(self):
        sys.modules.pop("backend.settings.prod", None)
        sys.modules.pop("backend.settings.base", None)
        sys.modules.pop("backend.settings", None)
        return importlib.import_module("backend.settings.prod")

    def test_prod_settings_reject_localhost_frontend_by_default(self) -> None:
        env = {
            "DJANGO_SECRET_KEY": self.VALID_SECRET_KEY,
            "FRONTEND_BASE_URL": "http://localhost",
            "DATABASE_URL": "sqlite:///tmp.sqlite3",
            "CORS_ALLOWED_ORIGINS": "http://localhost",
            "DJANGO_ALLOWED_HOSTS": (
                "localhost,127.0.0.1,api.localhost,admin.localhost"
            ),
            "DJANGO_CSRF_TRUSTED_ORIGINS": "http://localhost",
        }

        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(
                RuntimeError,
                "FRONTEND_BASE_URL must point to a non-localhost frontend",
            ):
                self._import_prod_settings()

    def test_prod_settings_allows_localhost_frontend_when_enabled(
        self,
    ) -> None:
        env = {
            "DJANGO_SECRET_KEY": self.VALID_SECRET_KEY,
            "FRONTEND_BASE_URL": "http://localhost",
            "DATABASE_URL": "sqlite:///tmp.sqlite3",
            "CORS_ALLOWED_ORIGINS": "http://localhost",
            "DJANGO_ALLOWED_HOSTS": (
                "localhost,127.0.0.1,api.localhost,admin.localhost"
            ),
            "DJANGO_CSRF_TRUSTED_ORIGINS": "http://localhost",
            "DJANGO_ALLOW_LOCALHOST_FRONTEND_BASE_URL": "true",
        }

        with patch.dict(os.environ, env, clear=True):
            prod = self._import_prod_settings()

        self.assertEqual(prod.FRONTEND_BASE_URL, "http://localhost")
