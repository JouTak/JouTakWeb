import warnings
from datetime import timedelta
from pathlib import Path

from corsheaders.defaults import default_headers
from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

from backend.settings.env import apply_env_file_overrides
from backend.settings.webauthn import (
    parse_webauthn_origins,
    validate_webauthn_configuration,
)

warnings.filterwarnings(
    "ignore",
    message=(
        "allauth.headless.tokens.base.AbstractTokenStrategy is deprecated*"
    ),
    category=UserWarning,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

apply_env_file_overrides(
    (
        "DJANGO_SECRET_KEY",
        "DATABASE_URL",
        "POSTGRES_PASSWORD",
        "YANDEX_CLIENT_ID",
        "YANDEX_SECRET",
        "GITHUB_CLIENT_ID",
        "GITHUB_SECRET",
        "EMAIL_HOST_PASSWORD",
        "SENTRY_DSN",
    )
)


DEBUG = config("DJANGO_DEBUG", cast=bool, default=False)
SECRET_KEY = config("DJANGO_SECRET_KEY", default="")
SITE_ID = config("DJANGO_SITE_ID", cast=int, default=1)
SITE_DOMAIN = config("DJANGO_SITE_DOMAIN", default="")
SITE_NAME = config("DJANGO_SITE_NAME", default="")

ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv()
)
DJANGO_ADMIN_HOSTS = config(
    "DJANGO_ADMIN_HOSTS",
    default="admin.joutak.ru,admin.localhost",
    cast=Csv(),
)
DJANGO_API_HOSTS = config(
    "DJANGO_API_HOSTS",
    default="joutak.ru,api.joutak.ru,api.localhost",
    cast=Csv(),
)
CSRF_TRUSTED_ORIGINS = config(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173",
    cast=Csv(),
)
INTERNAL_IPS = config("DJANGO_INTERNAL_IPS", default="127.0.0.1", cast=Csv())

INSTALLED_APPS = [
    "backend.admin.JouTakAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "django.contrib.humanize",
    "django.contrib.staticfiles",
    # Third-party
    "corsheaders",
    "axes",
    "simple_history",
    "ninja",
    "ninja_jwt",
    "ninja_jwt.token_blacklist",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.mfa",
    "allauth.headless",
    "allauth.usersessions",
    "allauth.socialaccount.providers.yandex",
    # Project apps
    "core.apps.CoreConfig",
    "accounts.apps.AccountsConfig",
    "featureflags.apps.FeatureFlagsConfig",
    "bff.apps.BffConfig",
    "observability.apps.ObservabilityConfig",
]

MIDDLEWARE = [
    "backend.middleware.RequestContextMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "backend.middleware.HostRoutingMiddleware",
    "backend.middleware.AdminSameOriginMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "accounts.middleware.WebAuthnOriginValidationMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
    "backend.middleware.AdminMFAEnforcementMiddleware",
    "allauth.usersessions.middleware.UserSessionsMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "backend.wsgi.application"

DATABASES = {}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        )
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {
        "NAME": (
            "django.contrib.auth.password_validation.CommonPasswordValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation.NumericPasswordValidator"
        )
    },
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
ACCOUNT_ADAPTER = "accounts.adapters.StrictAccountAdapter"
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = False

# ─── django-axes: brute-force login protection ─────────────────────────────
AXES_FAILURE_LIMIT = config("AXES_FAILURE_LIMIT", cast=int, default=5)
AXES_COOLOFF_TIME = timedelta(
    minutes=config("AXES_COOLOFF_MINUTES", cast=int, default=15)
)
AXES_LOCKOUT_PARAMETERS = [["ip_address", "username"]]
AXES_RESET_ON_SUCCESS = True
AXES_ENABLE_ACCESS_FAILURE_LOG = True

NINJA_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("JWT_ACCESS_MIN", cast=int, default=15)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config("JWT_REFRESH_DAYS", cast=int, default=30)
    ),
    "ROTATE_REFRESH_TOKENS": config(
        "JWT_ROTATE_REFRESH", cast=bool, default=True
    ),
    "BLACKLIST_AFTER_ROTATION": config(
        "JWT_BLACKLIST_AFTER_ROTATION", cast=bool, default=True
    ),
    "UPDATE_LAST_LOGIN": True,
}

JWT_REFRESH_COOKIE_NAME = config(
    "JWT_REFRESH_COOKIE_NAME", default="joutak_refresh"
)
JWT_REFRESH_COOKIE_DOMAIN = config("JWT_REFRESH_COOKIE_DOMAIN", default=None)
JWT_REFRESH_COOKIE_PATH = config(
    "JWT_REFRESH_COOKIE_PATH", default="/api/auth/refresh"
)
JWT_REFRESH_COOKIE_SECURE = config(
    "JWT_REFRESH_COOKIE_SECURE", cast=bool, default=not DEBUG
)
JWT_REFRESH_COOKIE_SAMESITE = config(
    "JWT_REFRESH_COOKIE_SAMESITE", default="Lax"
)
JWT_REFRESH_COOKIE_MAX_AGE = int(
    NINJA_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
)


ACCOUNT_LOGIN_METHODS = {"email", "username"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = config(
    "ACCOUNT_EMAIL_VERIFICATION", default="optional"
)
FRONTEND_BASE_URL = config(
    "FRONTEND_BASE_URL", default="http://localhost:5173"
)
_frontend_base = FRONTEND_BASE_URL.rstrip("/")
HEADLESS_FRONTEND_URLS = {
    "account_signup": (f"{_frontend_base}/login"),
    "account_confirm_email": (f"{_frontend_base}/confirm-email?key={{key}}"),
    "account_reset_password": (f"{_frontend_base}/reset-password"),
    "account_reset_password_from_key": (
        f"{_frontend_base}/reset-password?key={{key}}"
    ),
}
ACCOUNT_CHANGE_EMAIL = True

HEADLESS_ONLY = True


def _parse_headless_clients(raw: str) -> tuple[str, ...]:
    """Validate ``HEADLESS_CLIENTS`` env value.

    allauth's headless app only understands ``app`` and ``browser``. A
    typo or an empty string silently disables the headless endpoints
    we rely on, so we fail loudly at import time instead.
    """

    known = {"app", "browser"}
    values = tuple(
        item.strip().lower() for item in raw.split(",") if item.strip()
    )
    if not values:
        raise ImproperlyConfigured(
            "HEADLESS_CLIENTS must not be empty; allowed values: "
            f"{sorted(known)}."
        )
    unknown = sorted(set(values) - known)
    if unknown:
        raise ImproperlyConfigured(
            "HEADLESS_CLIENTS contains unsupported entries "
            f"{unknown}; allowed values: {sorted(known)}."
        )
    # De-dupe while preserving order.
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return tuple(result)


HEADLESS_CLIENTS = _parse_headless_clients(
    config("HEADLESS_CLIENTS", default="app")
)
HEADLESS_SERVE_SPECIFICATION = DEBUG
# Use the revocable strategy unconditionally: switching it off at runtime
# silently disables session-token revocation, which is a security
# regression and must not be configurable from the environment.
HEADLESS_TOKEN_STRATEGY = (
    "accounts.token_strategy.RevocableSessionTokenStrategy"
)

MFA_SUPPORTED_TYPES = ["totp", "webauthn", "recovery_codes"]
MFA_ADAPTER = "accounts.mfa_adapter.EncryptedMFAAdapter"
MFA_TOTP_ISSUER = config("MFA_TOTP_ISSUER", default="JouTak")
MFA_TOTP_PERIOD = config("MFA_TOTP_PERIOD", cast=int, default=30)
MFA_TOTP_TOLERANCE = config("MFA_TOTP_TOLERANCE", cast=int, default=1)
MFA_PASSKEY_LOGIN_ENABLED = config(
    "MFA_PASSKEY_LOGIN_ENABLED", cast=bool, default=True
)
MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN = DEBUG
(
    WEBAUTHN_RP_ID,
    WEBAUTHN_RP_NAME,
    WEBAUTHN_ACCOUNT_ORIGINS,
    WEBAUTHN_ADMIN_ORIGINS,
    WEBAUTHN_ALLOWED_ORIGINS,
) = validate_webauthn_configuration(
    rp_id=config("WEBAUTHN_RP_ID", default="localhost"),
    rp_name=config("WEBAUTHN_RP_NAME", default="JouTak"),
    account_origins=config(
        "WEBAUTHN_ACCOUNT_ORIGINS",
        default="http://localhost:5173,http://joutak.localhost",
        cast=parse_webauthn_origins,
    ),
    admin_origins=config(
        "WEBAUTHN_ADMIN_ORIGINS",
        default="http://admin.localhost,http://admin.localhost:8000",
        cast=parse_webauthn_origins,
    ),
    allowed_origins=config(
        "WEBAUTHN_ALLOWED_ORIGINS",
        default=(
            "http://localhost:5173,http://joutak.localhost,"
            "http://admin.localhost,http://admin.localhost:8000"
        ),
        cast=parse_webauthn_origins,
    ),
    require_https=False,
    allow_ports=True,
)
WEBAUTHN_CHALLENGE_TTL_SECONDS = config(
    "WEBAUTHN_CHALLENGE_TTL_SECONDS", cast=int, default=300
)
ADMIN_MFA_PENDING_TTL_SECONDS = config(
    "ADMIN_MFA_PENDING_TTL_SECONDS", cast=int, default=300
)
ADMIN_MFA_ASSURANCE_TTL_SECONDS = config(
    "ADMIN_MFA_ASSURANCE_TTL_SECONDS", cast=int, default=28800
)
ADMIN_MFA_COMPLETION_RATE = config("ADMIN_MFA_COMPLETION_RATE", default="5/m")
ADMIN_MFA_OPTIONS_RATE = config("ADMIN_MFA_OPTIONS_RATE", default="20/m")
MFA_ENCRYPTION_KEYS = tuple(
    value.strip()
    for value in config(
        "MFA_ENCRYPTION_KEYS",
        default=config("MFA_ENCRYPTION_KEY", default=""),
        cast=Csv(),
    )
    if value and value.strip()
)
MFA_ENCRYPTION_INCLUDE_LEGACY_SECRET_KEY = config(
    "MFA_ENCRYPTION_INCLUDE_LEGACY_SECRET_KEY",
    cast=bool,
    default=True,
)
MFA_ENCRYPTION_PREFIX = "fernet:"

ACCOUNT_TRUST_PROXY_HEADERS = config(
    "ACCOUNT_TRUST_PROXY_HEADERS", cast=bool, default=False
)
ACCOUNT_TRUSTED_PROXY_CIDRS = tuple(
    value.strip()
    for value in config("ACCOUNT_TRUSTED_PROXY_CIDRS", default="", cast=Csv())
    if value and value.strip()
)
AUTH_SESSION_RETENTION_DAYS = config(
    "AUTH_SESSION_RETENTION_DAYS", cast=int, default=30
)
AUTH_TOKEN_RETENTION_DAYS = config(
    "AUTH_TOKEN_RETENTION_DAYS", cast=int, default=30
)
OTEL_SERVICE_NAME = config("OTEL_SERVICE_NAME", default="joutak-backend")
OTEL_METRICS_EXPORT_INTERVAL_MS = config(
    "OTEL_METRICS_EXPORT_INTERVAL_MS",
    cast=int,
    default=60000,
)
FEATURE_FLAG_ANONYMOUS_ID_COOKIE = config(
    "FEATURE_FLAG_ANONYMOUS_ID_COOKIE", default="joutak_ffid"
)
FEATURE_FLAG_ANONYMOUS_ID_COOKIE_MAX_AGE = config(
    "FEATURE_FLAG_ANONYMOUS_ID_COOKIE_MAX_AGE",
    cast=int,
    default=60 * 60 * 24 * 365,
)
FEATURE_FLAG_OVERRIDE_COOKIE = config(
    "FEATURE_FLAG_OVERRIDE_COOKIE", default="joutak_ff_override"
)
FEATURE_FLAG_OVERRIDE_COOKIE_MAX_AGE = config(
    "FEATURE_FLAG_OVERRIDE_COOKIE_MAX_AGE",
    cast=int,
    # 30 days by default — feature overrides are a debug/staff tool, we
    # do not want a stale signed payload to survive indefinitely.
    default=60 * 60 * 24 * 30,
)

# ─── Caching ────────────────────────────────────────────────────────────────
# DatabaseCache works across Gunicorn workers without requiring Redis. Rate
# counters/epochs and WebAuthn replay claims use separate fail-closed tables:
# capacity exhaustion may deny a new ceremony, but must never evict live
# security state and silently mint fresh attempts or permit a replay.
CACHE_MAX_ENTRIES = config("CACHE_MAX_ENTRIES", cast=int, default=100000)
if CACHE_MAX_ENTRIES < 10000:
    raise ImproperlyConfigured(
        "CACHE_MAX_ENTRIES must be at least 10000 for shared security state."
    )
CACHES = {
    "default": {
        "BACKEND": "backend.cache_backends.FailClosedDatabaseCache",
        "LOCATION": "joutak_cache_table",
        "OPTIONS": {"MAX_ENTRIES": CACHE_MAX_ENTRIES},
    },
    "ratelimit": {
        "BACKEND": "backend.cache_backends.FailClosedDatabaseCache",
        "LOCATION": "joutak_ratelimit_cache_table",
        "OPTIONS": {"MAX_ENTRIES": CACHE_MAX_ENTRIES},
    },
    "webauthn_replay": {
        "BACKEND": "backend.cache_backends.FailClosedDatabaseCache",
        "LOCATION": "joutak_webauthn_replay_cache_table",
        "OPTIONS": {"MAX_ENTRIES": CACHE_MAX_ENTRIES},
    },
}

# ─── Rate limiting (django-ratelimit) ──────────────────────────────────────
RATELIMIT_USE_CACHE = "ratelimit"
RATELIMIT_FAIL_OPEN = config("RATELIMIT_FAIL_OPEN", cast=bool, default=False)
WEBAUTHN_REPLAY_CACHE_ALIAS = "webauthn_replay"

LANGUAGE_CODE = "ru-RU"
TIME_ZONE = config("DJANGO_TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
AVATAR_MAX_UPLOAD_BYTES = config(
    "AVATAR_MAX_UPLOAD_BYTES", cast=int, default=2 * 1024 * 1024
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

YANDEX_CLIENT_ID = config("YANDEX_CLIENT_ID", default="")
YANDEX_SECRET = config("YANDEX_SECRET", default="")
GITHUB_CLIENT_ID = config("GITHUB_CLIENT_ID", default="")
GITHUB_SECRET = config("GITHUB_SECRET", default="")

SOCIALACCOUNT_PROVIDERS = {
    "yandex": {
        "APPS": [
            {
                "client_id": YANDEX_CLIENT_ID,
                "secret": YANDEX_SECRET,
                "key": "",
                "settings": {"scope": ["login:email"]},
            }
        ],
    },
}

CORS_ALLOW_CREDENTIALS = True
CORS_URLS_REGEX = r"^/(?:api|bff)(?:/|$)"
CORS_ALLOW_HEADERS = [
    *default_headers,
    "x-session-token",
    "x-refresh-token",
    "x-client",
    "x-allauth-client",
    "x-email-verification-key",
    "x-password-reset-key",
    "authorization",
    "content-type",
]
CORS_EXPOSE_HEADERS = ["X-Session-Token"]

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=Csv())

# Profile personalization rollout flags
FF_PROFILE_PERSONALIZATION_UI = config(
    "FF_PROFILE_PERSONALIZATION_UI", cast=bool, default=True
)
FF_PROFILE_PERSONALIZATION_INTERSTITIAL = config(
    "FF_PROFILE_PERSONALIZATION_INTERSTITIAL", cast=bool, default=True
)
FF_PROFILE_PERSONALIZATION_ENFORCE = config(
    "FF_PROFILE_PERSONALIZATION_ENFORCE", cast=bool, default=False
)


def as_public_settings() -> dict[str, object]:
    return {name: value for name, value in globals().items() if name.isupper()}
