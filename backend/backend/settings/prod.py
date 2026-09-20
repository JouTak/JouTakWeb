from urllib.parse import urlparse

import dj_database_url
from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured
from django.http.request import is_same_domain
from observability.logging import build_logging_config

from . import base as base_settings
from .webauthn import (
    parse_webauthn_origins,
    validate_webauthn_configuration,
)

globals().update(base_settings.as_public_settings())


def _required(name: str) -> str:
    value = config(name, default="").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} is required in production.")
    return value


def _csrf_origin_covers_admin_origin(
    trusted_origin: str,
    admin_origin: str,
) -> bool:
    """Return whether Django's CSRF origin pattern trusts an admin origin."""
    trusted = urlparse(trusted_origin)
    admin = urlparse(admin_origin)
    try:
        trusted_port = trusted.port
        admin_port = admin.port
    except ValueError:
        return False
    trusted_host = (trusted.hostname or "").lower()
    admin_host = (admin.hostname or "").lower()
    if trusted.scheme != admin.scheme or trusted_port != admin_port:
        return False
    if "*" in trusted_origin:
        # Match CsrfViewMiddleware.allowed_origin_subdomains exactly: Django
        # strips every leading ``*`` from the netloc, then applies
        # is_same_domain(). This deliberately catches odd-but-effective forms
        # such as ``https://*admin.example`` as well as the documented ``*.``.
        return is_same_domain(
            admin.netloc.lower(),
            trusted.netloc.lower().lstrip("*"),
        )
    return trusted_host == admin_host


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
allow_localhost_frontend_base_url = config(
    "DJANGO_ALLOW_LOCALHOST_FRONTEND_BASE_URL",
    cast=bool,
    default=False,
)
if (
    parsed_frontend.hostname in {"localhost", "127.0.0.1"}
    and not allow_localhost_frontend_base_url
):
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
# Health check is consumed by the Docker/Swarm runtime over plain HTTP
# inside the container network. Excluding it from the SSL redirect keeps
# healthchecks green without loosening HSTS for real traffic.
SECURE_REDIRECT_EXEMPT = [r"^health/?$"]
SESSION_COOKIE_NAME = config(
    "SESSION_COOKIE_NAME", default="__Host-joutak_session"
)
if not SESSION_COOKIE_NAME.startswith("__Host-"):
    raise ImproperlyConfigured(
        "SESSION_COOKIE_NAME must use the __Host- prefix in production."
    )
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_PATH = "/"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_PATH = "/"

if config("USE_X_FORWARDED_PROTO", cast=bool, default=True):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", cast=int, default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SAMESITE = config("SESSION_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SAMESITE = config("CSRF_COOKIE_SAMESITE", default="Lax")
JWT_REFRESH_COOKIE_SAMESITE = (
    str(base_settings.JWT_REFRESH_COOKIE_SAMESITE).strip().capitalize()
)
if SESSION_COOKIE_SAMESITE not in {"Lax", "Strict"}:
    raise ImproperlyConfigured(
        "SESSION_COOKIE_SAMESITE must be Lax or Strict in production."
    )
if CSRF_COOKIE_SAMESITE not in {"Lax", "Strict"}:
    raise ImproperlyConfigured(
        "CSRF_COOKIE_SAMESITE must be Lax or Strict in production."
    )
if JWT_REFRESH_COOKIE_SAMESITE not in {"Lax", "Strict"}:
    raise ImproperlyConfigured(
        "JWT_REFRESH_COOKIE_SAMESITE must be Lax or Strict in production."
    )
_configured_session_cookie_domain = config(
    "SESSION_COOKIE_DOMAIN", default=None
)
_configured_csrf_cookie_domain = config("CSRF_COOKIE_DOMAIN", default=None)
_configured_jwt_refresh_cookie_domain = config(
    "JWT_REFRESH_COOKIE_DOMAIN", default=None
)
if (
    _configured_session_cookie_domain
    or _configured_csrf_cookie_domain
    or _configured_jwt_refresh_cookie_domain
):
    raise ImproperlyConfigured(
        "Production auth and CSRF cookies must be host-only; cookie Domain "
        "settings must be unset."
    )
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
JWT_REFRESH_COOKIE_DOMAIN = None
JWT_REFRESH_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

# CI/test runs use SQLite with this production settings module. Django admin
# templates need the collected manifest there, but the test jobs do not run
# collectstatic. Fall back to plain static files storage in that case only.
if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    STORAGES["staticfiles"] = {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    }

HEADLESS_SERVE_SPECIFICATION = False
MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN = config(
    "MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN",
    cast=bool,
    default=False,
)
if MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN:
    raise ImproperlyConfigured(
        "MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN must be false in production."
    )

(
    WEBAUTHN_RP_ID,
    WEBAUTHN_RP_NAME,
    WEBAUTHN_ACCOUNT_ORIGINS,
    WEBAUTHN_ADMIN_ORIGINS,
    WEBAUTHN_ALLOWED_ORIGINS,
) = validate_webauthn_configuration(
    rp_id=_required("WEBAUTHN_RP_ID"),
    rp_name=_required("WEBAUTHN_RP_NAME"),
    account_origins=parse_webauthn_origins(
        _required("WEBAUTHN_ACCOUNT_ORIGINS")
    ),
    admin_origins=parse_webauthn_origins(_required("WEBAUTHN_ADMIN_ORIGINS")),
    allowed_origins=parse_webauthn_origins(
        _required("WEBAUTHN_ALLOWED_ORIGINS")
    ),
    require_https=True,
    allow_ports=False,
)
if any(
    _csrf_origin_covers_admin_origin(trusted_origin, admin_origin)
    for trusted_origin in base_settings.CSRF_TRUSTED_ORIGINS
    for admin_origin in WEBAUTHN_ADMIN_ORIGINS
):
    raise ImproperlyConfigured(
        "Production admin origins must not appear in the global "
        "CSRF_TRUSTED_ORIGINS allowlist. Same-origin admin requests do not "
        "need that exception."
    )

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


LOGGING = build_logging_config(root_level="INFO")

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
