from communities.models import SLUG_VALIDATOR, Community
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from profiles.validators import (
    Visibility,
    validate_image_reference,
    validate_safe_url,
)

COORDINATE_VALIDATORS = [
    MinValueValidator(-30_000_000),
    MaxValueValidator(30_000_000),
]


class City(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        ACTIVE = "active", "Опубликован"
        ARCHIVED = "archived", "В архиве"

    class Recruitment(models.TextChoices):
        OPEN = "open", "Открыт для жителей"
        LIMITED = "limited", "Ограниченный набор"
        CLOSED = "closed", "Набор закрыт"

    community = models.ForeignKey(
        Community,
        on_delete=models.PROTECT,
        related_name="cities",
    )
    slug = models.SlugField(
        max_length=80,
        unique=True,
        validators=[SLUG_VALIDATOR],
    )
    name = models.CharField(max_length=120)
    short_description = models.CharField(max_length=280)
    description = models.TextField(max_length=12000, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    recruitment_status = models.CharField(
        max_length=16,
        choices=Recruitment.choices,
        default=Recruitment.CLOSED,
    )
    founded_at = models.DateField(null=True, blank=True)
    region = models.CharField(max_length=120, blank=True)
    language = models.CharField(max_length=80, blank=True)
    how_to_join = models.TextField(max_length=2000, blank=True)
    logo_url = models.CharField(
        max_length=500,
        blank=True,
        validators=[validate_image_reference],
    )
    cover_url = models.CharField(
        max_length=500,
        blank=True,
        validators=[validate_image_reference],
    )
    world = models.CharField(max_length=80, blank=True)
    x = models.IntegerField(
        null=True, blank=True, validators=COORDINATE_VALIDATORS
    )
    y = models.IntegerField(
        null=True, blank=True, validators=COORDINATE_VALIDATORS
    )
    z = models.IntegerField(
        null=True, blank=True, validators=COORDINATE_VALIDATORS
    )
    map_id = models.CharField(max_length=80, blank=True)
    map_marker_id = models.CharField(max_length=120, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("name", "pk")
        permissions = [("moderate_city", "Moderate city governance")]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(x__isnull=True, z__isnull=True)
                    | models.Q(x__isnull=False, z__isnull=False)
                ),
                name="city_coordinate_pair",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["draft", "active", "archived"]),
                name="city_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    recruitment_status__in=["open", "limited", "closed"]
                ),
                name="city_recruitment_valid",
            ),
            models.CheckConstraint(
                condition=~models.Q(status="active", short_description=""),
                name="city_active_summary_required",
            ),
        ]

    def __str__(self):
        return self.name


class CityMembership(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        ACTIVE = "active", "Житель"
        LEFT = "left", "Вышел"
        REMOVED = "removed", "Исключён"

    class Role(models.TextChoices):
        RESIDENT = "resident", "Житель"
        REPRESENTATIVE = "representative", "Представитель"
        MANAGER = "manager", "Управляющий"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="city_memberships",
    )
    city = models.ForeignKey(
        City, on_delete=models.PROTECT, related_name="memberships"
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    role = models.CharField(
        max_length=16, choices=Role.choices, default=Role.RESIDENT
    )
    position = models.CharField(max_length=100, blank=True)
    visibility = models.CharField(
        max_length=16,
        choices=Visibility.choices,
        default=Visibility.COMMUNITY,
    )
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "city"), name="city_member_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["pending", "active", "left", "removed"]
                ),
                name="city_member_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    role__in=["resident", "representative", "manager"]
                ),
                name="city_member_role_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["city", "status", "role"]),
            models.Index(fields=["user", "status"]),
        ]


class CityContact(models.Model):
    class Type(models.TextChoices):
        DISCORD = "discord", "Discord"
        TELEGRAM = "telegram", "Telegram"
        VK = "vk", "VK"
        WEBSITE = "website", "Сайт"
        OTHER = "other", "Ссылка"

    city = models.ForeignKey(
        City, on_delete=models.CASCADE, related_name="contacts"
    )
    type = models.CharField(max_length=16, choices=Type.choices)
    label = models.CharField(max_length=100)
    url = models.URLField(max_length=500, validators=[validate_safe_url])
    visibility = models.CharField(
        max_length=16,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "pk")


class CityInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает ответа"
        ACCEPTED = "accepted", "Принято"
        DECLINED = "declined", "Отклонено"
        REVOKED = "revoked", "Отозвано"

    city = models.ForeignKey(
        City, on_delete=models.CASCADE, related_name="invitations"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="city_invitations_sent",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        constraints = [
            models.UniqueConstraint(
                fields=["city", "user"],
                condition=models.Q(status="pending"),
                name="city_invitation_pending_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["pending", "accepted", "declined", "revoked"]
                ),
                name="city_invitation_status_valid",
            ),
        ]
        indexes = [models.Index(fields=["user", "status", "expires_at"])]


class CityRevision(models.Model):
    city = models.ForeignKey(
        City, on_delete=models.PROTECT, related_name="revisions"
    )
    version = models.PositiveIntegerField()
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    content = models.JSONField()
    changed_fields = models.JSONField(default=list)

    class Meta:
        ordering = ("-version",)
        constraints = [
            models.UniqueConstraint(
                fields=("city", "version"), name="city_revision_unique"
            )
        ]


class CityAuditEvent(models.Model):
    city = models.ForeignKey(
        City, on_delete=models.PROTECT, related_name="audit_events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    action = models.CharField(max_length=48)
    target_membership_id = models.BigIntegerField(null=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        indexes = [models.Index(fields=["city", "created_at"])]
