from pathlib import Path

import dj_database_url
from decouple import Csv, config
from observability.logging import build_logging_config

from . import base as base_settings

globals().update(base_settings.as_public_settings())

DEBUG = True
if not base_settings.SECRET_KEY:
    SECRET_KEY = "dev-only-insecure-secret-key-change-me"

ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS",
    default=(
        "127.0.0.1,localhost,joutak.localhost,api.localhost,admin.localhost"
    ),
    cast=Csv(),
)
CSRF_TRUSTED_ORIGINS = config(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default=(
        "http://localhost,http://localhost:5173,"
        "http://127.0.0.1,http://127.0.0.1:5173,"
        "http://joutak.localhost,http://api.localhost,"
        "http://api.localhost:8000,http://admin.localhost,"
        "http://admin.localhost:8000"
    ),
    cast=Csv(),
)
CORS_ALLOW_ALL_ORIGINS = config(
    "CORS_ALLOW_ALL_ORIGINS",
    cast=bool,
    default=True,
)

# Compose supplies DATABASE_URL for its PostgreSQL service. Keeping the
# SQLite fallback makes a native backend checkout zero-configuration.
DATABASE_URL = config("DATABASE_URL", default="").strip()
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=config("DB_CONN_MAX_AGE", cast=int, default=0),
            ssl_require=config("DB_SSL_REQUIRED", cast=bool, default=False),
        )
    }
    DATABASES["default"]["ATOMIC_REQUESTS"] = True
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": base_settings.BASE_DIR / "db.sqlite3",
        }
    }

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# In dev, use in-memory cache (no need for cache table with SQLite).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
# base.py is imported before DEBUG is overridden above, so cookie defaults
# derived from base_settings.DEBUG would otherwise stay production-secure.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
JWT_REFRESH_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

# Compose keeps uploaded files outside the read-only source bind. Native
# development retains Django's usual backend/media location.
MEDIA_ROOT = Path(config("MEDIA_ROOT", default=str(base_settings.MEDIA_ROOT)))

HEADLESS_SERVE_SPECIFICATION = True
MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN = config(
    "MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN",
    cast=bool,
    default=True,
)

LOGGING = build_logging_config(root_level="DEBUG")
