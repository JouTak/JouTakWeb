import warnings
from datetime import timedelta
from pathlib import Path

from corsheaders.defaults import default_headers
from decouple import Csv, config

warnings.filterwarnings(
    "ignore",
    message=(
        "allauth.headless.tokens.base.AbstractTokenStrategy is deprecated*"
    ),
    category=UserWarning,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent


DEBUG = config("DJANGO_DEBUG", cast=bool, default=False)
SECRET_KEY = config("DJANGO_SECRET_KEY", default="")
ALLOW_REVERSE = config("DJANGO_ALLOW_REVERSE", cast=bool, default=True)

ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv()
)
CSRF_TRUSTED_ORIGINS = config(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173",
    cast=Csv(),
)
INTERNAL_IPS = config("DJANGO_INTERNAL_IPS", default="127.0.0.1", cast=Csv())

SITE_ID = config("DJANGO_SITE_ID", cast=int, default=1)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "django.contrib.humanize",
    "django.contrib.staticfiles",
    # Third-party
    "corsheaders",
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
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.usersessions.middleware.UserSessionsMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

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


ACCOUNT_LOGIN_METHODS = {"username"}
ACCOUNT_SIGNUP_FIELDS = ["email", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = config(
    "ACCOUNT_EMAIL_VERIFICATION", default="optional"
)
HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": "http://localhost:5173/confirm-email?key={key}",
    "account_reset_password": "http://localhost:5173/reset-password?key={key}",
}
ACCOUNT_CHANGE_EMAIL = True

HEADLESS_ONLY = True
HEADLESS_CLIENTS = tuple(config("HEADLESS_CLIENTS", default="app", cast=Csv()))
HEADLESS_SERVE_SPECIFICATION = DEBUG
HEADLESS_TOKEN_STRATEGY = config(
    "HEADLESS_TOKEN_STRATEGY",
    default="allauth.headless.tokens.strategies.sessions.SessionTokenStrategy",
)

MFA_SUPPORTED_TYPES = ["totp", "webauthn", "recovery_codes"]
MFA_TOTP_ISSUER = config("MFA_TOTP_ISSUER", default="JouTak")
MFA_TOTP_PERIOD = config("MFA_TOTP_PERIOD", cast=int, default=30)
MFA_TOTP_TOLERANCE = config("MFA_TOTP_TOLERANCE", cast=int, default=1)
MFA_PASSKEY_LOGIN_ENABLED = config(
    "MFA_PASSKEY_LOGIN_ENABLED", cast=bool, default=True
)
MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN = DEBUG

LANGUAGE_CODE = "ru-RU"
TIME_ZONE = config("DJANGO_TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

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
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-session-token",
    "x-refresh-token",
    "x-client",
    "x-allauth-client",
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
