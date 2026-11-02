from communities.models import SLUG_VALIDATOR
from django.conf import settings
from django.db import models
from profiles.validators import validate_image_reference, validate_safe_url


class PlayerGroup(models.Model):
    class Category(models.TextChoices):
        CLUB = "club", "Клуб"
        TEAM = "team", "Команда"
        GUILD = "guild", "Гильдия"

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        ACTIVE = "active", "Опубликовано"
        ARCHIVED = "archived", "В архиве"

    class Access(models.TextChoices):
        PUBLIC = "public", "Публичное"
        UNLISTED = "unlisted", "По ссылке"
        PRIVATE = "private", "Закрытое"

    class JoinMode(models.TextChoices):
        OPEN = "open", "Свободное вступление"
        APPROVAL = "approval", "По заявке"
        INVITE_ONLY = "invite_only", "По приглашению"

    class Audience(models.TextChoices):
        PUBLIC = "public", "Все"
        MEMBERS = "members", "Участники"
        PRIVATE = "private", "Только руководство"

    slug = models.SlugField(
        max_length=80, unique=True, validators=[SLUG_VALIDATOR]
    )
    name = models.CharField(max_length=120)
    short_description = models.CharField(max_length=280)
    description = models.TextField(max_length=12000, blank=True)
    rules = models.TextField(max_length=3000, blank=True)
    application_question = models.CharField(max_length=300, blank=True)
    welcome = models.TextField(max_length=3000, blank=True)
    logo_url = models.CharField(
        max_length=500, blank=True, validators=[validate_image_reference]
    )
    cover_url = models.CharField(
        max_length=500, blank=True, validators=[validate_image_reference]
    )
    category = models.CharField(
        max_length=12, choices=Category.choices, default=Category.CLUB
    )
    scope = models.ForeignKey(
        "communities.Community",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="player_groups",
    )
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.DRAFT
    )
    access = models.CharField(
        max_length=12, choices=Access.choices, default=Access.PUBLIC
    )
    join_mode = models.CharField(
        max_length=16, choices=JoinMode.choices, default=JoinMode.INVITE_ONLY
    )
    accepting = models.BooleanField(default=False)
    restricted = models.BooleanField(default=False)
    moderation_reason = models.CharField(max_length=500, blank=True)
    roster_visibility = models.CharField(
        max_length=12, choices=Audience.choices, default=Audience.MEMBERS
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_player_groups",
    )
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("name", "pk")
        permissions = [("moderate_playergroup", "Moderate player groups")]
        indexes = [models.Index(fields=["status", "access"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["draft", "active", "archived"]),
                name="group_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    access__in=["public", "unlisted", "private"]
                ),
                name="group_access_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    join_mode__in=["open", "approval", "invite_only"]
                ),
                name="group_join_mode_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(category__in=["club", "team", "guild"]),
                name="group_category_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    roster_visibility__in=["public", "members", "private"]
                ),
                name="group_roster_valid",
            ),
            models.CheckConstraint(
                condition=~models.Q(access="private")
                | models.Q(join_mode="invite_only"),
                name="group_private_invitation_only",
            ),
        ]

    def __str__(self):
        return self.name


class GroupContact(models.Model):
    group = models.ForeignKey(
        PlayerGroup, on_delete=models.CASCADE, related_name="contacts"
    )
    type = models.CharField(
        max_length=16,
        choices=[
            ("discord", "Discord"),
            ("telegram", "Telegram"),
            ("vk", "VK"),
        ],
    )
    label = models.CharField(max_length=100)
    url = models.URLField(max_length=500, validators=[validate_safe_url])
    visibility = models.CharField(
        max_length=12,
        choices=[("public", "Все"), ("members", "Участники")],
        default="members",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "pk")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(type__in=["discord", "telegram", "vk"]),
                name="group_contact_type_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(visibility__in=["public", "members"]),
                name="group_contact_visibility_valid",
            ),
        ]
