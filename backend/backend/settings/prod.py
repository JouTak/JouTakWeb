from urllib.parse import urlparse

import dj_database_url
from decouple import Csv, config

from . import base as base_settings

globals().update(base_settings.as_public_settings())

DEBUG = False
if (
    not base_settings.SECRET_KEY
    or base_settings.SECRET_KEY == "VERY_LONG_PASS_>80!TODO_CHANGE_ME!"
):
    raise RuntimeError(
        "A non-default DJANGO_SECRET_KEY is required in production"
    )

frontend_base_url = (base_settings.FRONTEND_BASE_URL or "").strip()
if not frontend_base_url:
    raise RuntimeError("FRONTEND_BASE_URL is required in production")

parsed_frontend = urlparse(
    frontend_base_url
    if "://" in frontend_base_url
    else f"https://{frontend_base_url}"
)
if parsed_frontend.hostname in {"localhost", "127.0.0.1"}:
    raise RuntimeError(
        "FRONTEND_BASE_URL must point to a non-localhost frontend "
        "in production"
    )

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", cast=Csv(), default="")

DATABASE_URL = config("DATABASE_URL", default="")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required in production")

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=config("DB_CONN_MAX_AGE", cast=int, default=600),
        ssl_require=config("DB_SSL_REQUIRED", cast=bool, default=True),
    )
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", cast=bool, default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

if config("USE_X_FORWARDED_PROTO", cast=bool, default=True):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", cast=int, default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SAMESITE = config("SESSION_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SAMESITE = config("CSRF_COOKIE_SAMESITE", default="Lax")

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

HEADLESS_SERVE_SPECIFICATION = False
MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN = False

EMAIL_BACKEND = config(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", cast=int, default=587)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_SSL = config("EMAIL_USE_SSL", cast=bool, default=False)
EMAIL_USE_TLS = config(
    "EMAIL_USE_TLS",
    cast=bool,
    default=(not EMAIL_USE_SSL),
)
EMAIL_TIMEOUT = config("EMAIL_TIMEOUT", cast=int, default=10)
if EMAIL_USE_SSL and EMAIL_USE_TLS:
    raise RuntimeError("EMAIL_USE_SSL and EMAIL_USE_TLS cannot both be true")
DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL",
    default=(EMAIL_HOST_USER or "noreply@example.com"),
)
SERVER_EMAIL = config("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=config("SENTRY_TRACES", cast=float, default=0.0),
        profiles_sample_rate=config(
            "SENTRY_PROFILES", cast=float, default=0.0
        ),
        send_default_pii=False,
    )
