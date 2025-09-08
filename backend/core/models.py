from django.conf import settings
from django.db import models


class UserSessionMeta(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="session_meta",
    )
    session_key = models.CharField(max_length=64, db_index=True)
    session_token = models.CharField(
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
        indexes = [
            models.Index(fields=["user", "session_key"]),
            models.Index(fields=["user", "session_token"]),
        ]


class UserSessionToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="session_tokens",
    )
    session_key = models.CharField(max_length=64, db_index=True)
    refresh_jti = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "session_key"])]
