from datetime import datetime
from datetime import timezone as dt_timezone

from django.conf import settings
from django.db import models

from profiles.validators import Visibility, validate_image_reference


class CommunityProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="community_profile",
    )
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(max_length=2000, blank=True)
    avatar_url = models.CharField(
        max_length=500,
        blank=True,
        validators=[validate_image_reference],
    )
    visibility = models.CharField(
        max_length=16,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    minecraft_visibility = models.CharField(
        max_length=16,
        choices=Visibility.choices,
        default=Visibility.COMMUNITY,
    )
    social_visibility = models.CharField(
        max_length=16,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    itmo_visibility = models.CharField(
        max_length=16,
        choices=Visibility.choices,
        default=Visibility.COMMUNITY,
    )
    memberships_visibility = models.CharField(
        max_length=16,
        choices=Visibility.choices,
        default=Visibility.COMMUNITY,
    )
    connections_visibility = models.CharField(
        max_length=16, choices=Visibility.choices, default=Visibility.PRIVATE
    )
    # Baseline until the server integration supplies actual first joins.
    # Not website registration; not editable through the self-profile API.
    minecraft_first_joined_at = models.DateTimeField(
        default=datetime(2026, 1, 1, tzinfo=dt_timezone.utc)
    )
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)
    contacts_version = models.PositiveIntegerField(default=1)
    legacy_vk_enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username


class ProfileFollow(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile_follows",
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile_followers",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "target"], name="profile_follow_unique"
            ),
            models.CheckConstraint(
                condition=~models.Q(user=models.F("target")),
                name="profile_follow_not_self",
            ),
        ]


class ProfileContact(models.Model):
    class Type(models.TextChoices):
        DISCORD = "discord", "Discord"
        TELEGRAM = "telegram", "Telegram"
        VK = "vk", "VK"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile_contacts",
    )
    type = models.CharField(max_length=16, choices=Type.choices)
    value = models.CharField(max_length=200)
    visibility = models.CharField(
        max_length=16, choices=Visibility.choices, default=Visibility.PRIVATE
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["type"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "type"], name="profile_contact_unique_type"
            ),
            models.CheckConstraint(
                condition=models.Q(type__in=["discord", "telegram", "vk"]),
                name="profile_contact_type_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(visibility__in=Visibility.values),
                name="profile_contact_visibility_valid",
            ),
        ]
