from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models, transaction
from profiles.validators import Visibility, validate_safe_url
from simple_history.models import HistoricalRecords

SLUG_VALIDATOR = RegexValidator(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class Community(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Активно"
        ARCHIVED = "archived", "В архиве"

    slug = models.SlugField(
        max_length=80,
        unique=True,
        validators=[SLUG_VALIDATOR],
    )
    name = models.CharField(max_length=120)
    short_description = models.CharField(max_length=280, blank=True)
    description = models.TextField(max_length=12000, blank=True)
    enrollment_text = models.TextField(max_length=3000, blank=True)
    enrollment_url = models.URLField(
        max_length=500, blank=True, validators=[validate_safe_url]
    )
    logo_url = models.URLField(
        max_length=500,
        blank=True,
        validators=[validate_safe_url],
    )
    cover_url = models.URLField(
        max_length=500,
        blank=True,
        validators=[validate_safe_url],
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    visibility = models.CharField(
        max_length=16,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "pk")

    def __str__(self):
        return self.name


class CommunityMembership(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        ACTIVE = "active", "Участник"
        LEFT = "left", "Вышел"
        SUSPENDED = "suspended", "Приостановлено"

    class Role(models.TextChoices):
        MEMBER = "member", "Участник"
        MODERATOR = "moderator", "Модератор сообщества"
        ADMIN = "admin", "Администратор сообщества"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="community_memberships",
    )
    community = models.ForeignKey(
        Community,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    role = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "community"),
                name="community_member_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "pending",
                        "active",
                        "left",
                        "suspended",
                    ]
                ),
                name="community_member_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=["member", "moderator", "admin"]),
                name="community_member_role_valid",
            ),
        ]
        indexes = [models.Index(fields=["user", "status"])]

    def __str__(self):
        return f"{self.user.username} · {self.community}"

    @transaction.atomic
    def save(self, *args, **kwargs):
        # Keep governance checks and the write in the same transaction.
        return super().save(*args, **kwargs)
