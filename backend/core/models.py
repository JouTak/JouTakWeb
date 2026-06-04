from django.conf import settings
from django.db import models
from django.utils.crypto import constant_time_compare, salted_hmac

SESSION_TOKEN_DIGEST_SALT = "core.UserSessionMeta.session_token.v1"


def session_token_digest(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    return salted_hmac(SESSION_TOKEN_DIGEST_SALT, raw).hexdigest()


def session_token_digest_matches(
    digest: str | None,
    value: str | None,
) -> bool:
    candidate = session_token_digest(value)
    return bool(
        digest and candidate and constant_time_compare(digest, candidate)
    )


class UserSessionMeta(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="session_meta",
    )
    session_key = models.CharField(max_length=64, db_index=True)
    session_token = models.CharField(max_length=64, null=True, blank=True)
    session_token_digest = models.CharField(
        max_length=64, null=True, blank=True, db_index=True
    )
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    ip = models.GenericIPAddressField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        unique_together = (("user", "session_key"),)
        indexes = (
            models.Index(fields=["user", "session_key"]),
            models.Index(fields=["user", "session_token_digest"]),
        )

    def save(self, *args, **kwargs):
        if self.session_token:
            self.session_token_digest = session_token_digest(
                self.session_token
            )
            self.session_token = None
        super().save(*args, **kwargs)


class UserSessionToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="session_tokens",
    )
    session_key = models.CharField(max_length=64, db_index=True)
    refresh_jti = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Refresh-token expiry mirrored from the JWT `exp` claim. Having it
    # on the row lets `cleanup_auth_data` purge aged mappings with a
    # single indexed filter instead of joining against
    # `OutstandingToken`, and it is cheap to maintain because we know
    # the lifetime at row creation time. Nullable to keep the migration
    # backfill-free on old data.
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = (models.Index(fields=["user", "session_key"]),)


class UserProfile(models.Model):
    PERSONALIZATION_ORIGIN_SIGNUP = "signup"
    PERSONALIZATION_ORIGIN_LEGACY = "legacy"
    PERSONALIZATION_ORIGIN_CHOICES = (
        (PERSONALIZATION_ORIGIN_SIGNUP, "Signup"),
        (PERSONALIZATION_ORIGIN_LEGACY, "Legacy"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="extended_profile",
    )
    vk_username = models.CharField(max_length=128, blank=True, default="")
    minecraft_nick = models.CharField(max_length=16, blank=True, default="")
    minecraft_has_license = models.BooleanField(null=True, blank=True)
    is_itmo_student = models.BooleanField(null=True, blank=True)
    itmo_isu = models.CharField(max_length=32, null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    personalization_origin = models.CharField(
        max_length=16,
        choices=PERSONALIZATION_ORIGIN_CHOICES,
        default=PERSONALIZATION_ORIGIN_SIGNUP,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = (
            models.Index(
                fields=["user", "updated_at"],
                name="core_userpr_user_id_557362_idx",
            ),
            models.Index(
                fields=["is_itmo_student"],
                name="core_userpr_is_itmo_17f9c2_idx",
            ),
        )
