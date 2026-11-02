from django.conf import settings
from django.db import models
from django.utils import timezone


class GroupMembership(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Участник"
        LEFT = "left", "Вышел"
        REMOVED = "removed", "Участие прекращено"

    class Role(models.TextChoices):
        MEMBER = "member", "Участник"
        MODERATOR = "moderator", "Модератор"
        MANAGER = "manager", "Руководитель"

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Все"
        MEMBERS = "members", "Участники объединения"
        PRIVATE = "private", "Только я и руководство"

    group = models.ForeignKey(
        "playergroups.PlayerGroup",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="group_memberships",
    )
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.ACTIVE
    )
    role = models.CharField(
        max_length=12, choices=Role.choices, default=Role.MEMBER
    )
    visibility = models.CharField(
        max_length=12, choices=Visibility.choices, default=Visibility.PRIVATE
    )
    first_joined_at = models.DateTimeField(default=timezone.now)
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "user"], name="group_membership_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["active", "left", "removed"]),
                name="group_membership_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    role__in=["member", "moderator", "manager"]
                ),
                name="group_membership_role_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    visibility__in=["public", "members", "private"]
                ),
                name="group_membership_visibility_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["group", "status", "role"]),
        ]


class GroupRestriction(models.Model):
    group = models.ForeignKey(
        "playergroups.PlayerGroup",
        on_delete=models.CASCADE,
        related_name="restrictions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="group_restrictions",
    )
    active = models.BooleanField(default=True)
    until = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=500)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="issued_group_restrictions",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "user"], name="group_restriction_unique"
            )
        ]
