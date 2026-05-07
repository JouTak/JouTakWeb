from observability.logging import build_logging_config

from . import base as base_settings

globals().update(base_settings.as_public_settings())

DEBUG = True
if not base_settings.SECRET_KEY:
    SECRET_KEY = "dev-only-insecure-secret-key-change-me"

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "api.localhost",
    "admin.localhost",
]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost",
    "http://api.localhost",
    "http://admin.localhost",
]
CORS_ALLOW_ALL_ORIGINS = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": base_settings.BASE_DIR / "db.sqlite3",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

HEADLESS_SERVE_SPECIFICATION = True
MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN = True

LOGGING = build_logging_config(root_level="DEBUG")
