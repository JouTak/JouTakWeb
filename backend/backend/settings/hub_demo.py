"""Isolated local Community Hub demo; never points at the normal dev DB."""

from . import dev as dev_settings

globals().update(
    {
        name: value
        for name, value in vars(dev_settings).items()
        if name.isupper()
    }
)
HUB_DEMO_MODE = True
HUB_DEMO_DATABASE = (
    dev_settings.BASE_DIR.parent / ".local" / "community-hub.sqlite3"
)
HUB_DEMO_DATABASE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": HUB_DEMO_DATABASE,
        # Parallel browser reads touch session metadata. Acquire SQLite's write
        # lock at transaction entry instead of racing deferred lock upgrades.
        "OPTIONS": {"timeout": 20, "transaction_mode": "IMMEDIATE"},
    }
}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ACCOUNT_RATE_LIMITS = False
MEDIA_ROOT = dev_settings.BASE_DIR.parent / ".local" / "media"
