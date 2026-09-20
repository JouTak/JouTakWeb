from __future__ import annotations

import importlib
import os
import sys
from unittest import TestCase
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured


class ProdSettingsFrontendBaseUrlTests(TestCase):
    VALID_SECRET_KEY = "test-secret-key-change-me-please-very-long-1234567890"

    @classmethod
    def _valid_env(cls) -> dict[str, str]:
        return {
            "DJANGO_SECRET_KEY": cls.VALID_SECRET_KEY,
            "FRONTEND_BASE_URL": "https://joutak.ru",
            "DATABASE_URL": "sqlite:///tmp.sqlite3",
            "CORS_ALLOWED_ORIGINS": "https://joutak.ru",
            "DJANGO_ALLOWED_HOSTS": (
                "joutak.ru,api.joutak.ru,admin.joutak.ru"
            ),
            "DJANGO_CSRF_TRUSTED_ORIGINS": "https://joutak.ru",
            "WEBAUTHN_RP_ID": "joutak.ru",
            "WEBAUTHN_RP_NAME": "JouTak",
            "WEBAUTHN_ACCOUNT_ORIGINS": "https://joutak.ru",
            "WEBAUTHN_ADMIN_ORIGINS": "https://admin.joutak.ru",
            "WEBAUTHN_ALLOWED_ORIGINS": (
                "https://joutak.ru,https://admin.joutak.ru"
            ),
        }

    def _import_prod_settings(self):
        sys.modules.pop("backend.settings.prod", None)
        sys.modules.pop("backend.settings.base", None)
        sys.modules.pop("backend.settings", None)
        return importlib.import_module("backend.settings.prod")

    def test_prod_settings_reject_localhost_frontend_by_default(self) -> None:
        env = {
            **self._valid_env(),
            "FRONTEND_BASE_URL": "http://localhost",
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
            **self._valid_env(),
            "FRONTEND_BASE_URL": "http://localhost",
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

    def test_prod_settings_pin_canonical_webauthn_and_host_only_cookie(
        self,
    ) -> None:
        with patch.dict(os.environ, self._valid_env(), clear=True):
            prod = self._import_prod_settings()

        self.assertEqual(prod.WEBAUTHN_RP_ID, "joutak.ru")
        self.assertEqual(prod.WEBAUTHN_RP_NAME, "JouTak")
        self.assertEqual(
            prod.CSRF_TRUSTED_ORIGINS,
            ["https://joutak.ru"],
        )
        self.assertEqual(
            prod.WEBAUTHN_ALLOWED_ORIGINS,
            ("https://joutak.ru", "https://admin.joutak.ru"),
        )
        self.assertEqual(prod.SESSION_COOKIE_NAME, "__Host-joutak_session")
        self.assertIsNone(prod.SESSION_COOKIE_DOMAIN)
        self.assertIsNone(prod.CSRF_COOKIE_DOMAIN)
        self.assertTrue(prod.SESSION_COOKIE_SECURE)
        self.assertEqual(prod.SESSION_COOKIE_PATH, "/")
        self.assertTrue(prod.JWT_REFRESH_COOKIE_SECURE)
        self.assertEqual(prod.JWT_REFRESH_COOKIE_SAMESITE, "Lax")
        self.assertEqual(
            prod.CACHES["default"]["OPTIONS"],
            {"MAX_ENTRIES": 100000},
        )
        self.assertEqual(
            prod.CACHES["default"]["BACKEND"],
            "backend.cache_backends.FailClosedDatabaseCache",
        )
        self.assertEqual(prod.RATELIMIT_USE_CACHE, "ratelimit")
        self.assertEqual(
            prod.WEBAUTHN_REPLAY_CACHE_ALIAS,
            "webauthn_replay",
        )
        self.assertEqual(
            prod.CACHES["ratelimit"]["BACKEND"],
            "backend.cache_backends.FailClosedDatabaseCache",
        )
        self.assertEqual(
            prod.CACHES["webauthn_replay"]["BACKEND"],
            "backend.cache_backends.FailClosedDatabaseCache",
        )
        locations = {config["LOCATION"] for config in prod.CACHES.values()}
        self.assertEqual(len(locations), len(prod.CACHES))
        for alias in ("ratelimit", "webauthn_replay"):
            self.assertEqual(
                prod.CACHES[alias]["OPTIONS"]["MAX_ENTRIES"],
                100000,
            )

    def test_prod_settings_reject_admin_origin_in_global_csrf_trust(
        self,
    ) -> None:
        for trusted_origin in (
            "https://admin.joutak.ru",
            "https://*.joutak.ru",
            "https://*.admin.joutak.ru",
            "https://*admin.joutak.ru",
        ):
            with self.subTest(trusted_origin=trusted_origin):
                env = {
                    **self._valid_env(),
                    "DJANGO_CSRF_TRUSTED_ORIGINS": (
                        f"https://joutak.ru,{trusted_origin}"
                    ),
                }

                with patch.dict(os.environ, env, clear=True):
                    with self.assertRaisesRegex(
                        ImproperlyConfigured,
                        "admin origins must not appear",
                    ):
                        self._import_prod_settings()

    def test_prod_settings_reject_unsafe_shared_cache_capacity(self) -> None:
        env = {**self._valid_env(), "CACHE_MAX_ENTRIES": "9999"}

        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(
                ImproperlyConfigured,
                "CACHE_MAX_ENTRIES",
            ):
                self._import_prod_settings()

    def test_prod_settings_debug_env_cannot_weaken_refresh_cookie(
        self,
    ) -> None:
        env = {**self._valid_env(), "DJANGO_DEBUG": "true"}

        with patch.dict(os.environ, env, clear=True):
            prod = self._import_prod_settings()

        self.assertFalse(prod.DEBUG)
        self.assertTrue(prod.JWT_REFRESH_COOKIE_SECURE)

    def test_prod_settings_explicit_false_cannot_weaken_refresh_cookie(
        self,
    ) -> None:
        env = {
            **self._valid_env(),
            "JWT_REFRESH_COOKIE_SECURE": "false",
        }

        with patch.dict(os.environ, env, clear=True):
            prod = self._import_prod_settings()

        self.assertTrue(prod.JWT_REFRESH_COOKIE_SECURE)

    def test_prod_settings_normalize_and_validate_refresh_samesite(
        self,
    ) -> None:
        env = {
            **self._valid_env(),
            "JWT_REFRESH_COOKIE_SAMESITE": "strict",
        }
        with patch.dict(os.environ, env, clear=True):
            prod = self._import_prod_settings()
        self.assertEqual(prod.JWT_REFRESH_COOKIE_SAMESITE, "Strict")

        env["JWT_REFRESH_COOKIE_SAMESITE"] = "None"
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(
                ImproperlyConfigured,
                "JWT_REFRESH_COOKIE_SAMESITE",
            ):
                self._import_prod_settings()

    def test_prod_settings_require_explicit_webauthn_config(self) -> None:
        env = self._valid_env()
        env.pop("WEBAUTHN_RP_ID")

        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(
                ImproperlyConfigured, "WEBAUTHN_RP_ID"
            ):
                self._import_prod_settings()

    def test_prod_settings_reject_invalid_rp_ids(self) -> None:
        for invalid in (
            "https://joutak.ru",
            "joutak.ru:443",
            "joutak.ru/path",
            "*.joutak.ru",
            "JOUTAK.RU",
        ):
            with self.subTest(invalid=invalid):
                env = {**self._valid_env(), "WEBAUTHN_RP_ID": invalid}
                with patch.dict(os.environ, env, clear=True):
                    with self.assertRaisesRegex(
                        ImproperlyConfigured, "WEBAUTHN_RP_ID"
                    ):
                        self._import_prod_settings()

    def test_prod_settings_reject_insecure_or_hostile_origins(self) -> None:
        for invalid in (
            "http://joutak.ru",
            "https://*.joutak.ru",
            "https://joutak.ru/path",
            "https://joutak.ru:443",
            "https://joutak.ru.evil.example",
            "https://joutak.ru?",
            "https://joutak.ru#",
            "https://joutak.ru?#",
            "https://joutak.ru:",
        ):
            with self.subTest(invalid=invalid):
                env = {
                    **self._valid_env(),
                    "WEBAUTHN_ACCOUNT_ORIGINS": invalid,
                }
                with patch.dict(os.environ, env, clear=True):
                    with self.assertRaises(ImproperlyConfigured):
                        self._import_prod_settings()

    def test_prod_settings_reject_parent_domain_cookies(self) -> None:
        for setting in (
            "SESSION_COOKIE_DOMAIN",
            "CSRF_COOKIE_DOMAIN",
            "JWT_REFRESH_COOKIE_DOMAIN",
        ):
            with self.subTest(setting=setting):
                env = {**self._valid_env(), setting: ".joutak.ru"}
                with patch.dict(os.environ, env, clear=True):
                    with self.assertRaisesRegex(
                        ImproperlyConfigured, "host-only"
                    ):
                        self._import_prod_settings()

    def test_prod_settings_reject_non_host_prefixed_session_name(self) -> None:
        env = {**self._valid_env(), "SESSION_COOKIE_NAME": "sessionid"}

        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(ImproperlyConfigured, "__Host-"):
                self._import_prod_settings()
