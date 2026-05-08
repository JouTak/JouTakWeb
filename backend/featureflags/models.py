from __future__ import annotations

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords


class FeatureKind(models.TextChoices):
    BOOLEAN = "boolean", "Boolean"
    VARIANT = "variant", "Variant"


class FeatureRuleType(models.TextChoices):
    EVERYONE = "everyone", "Everyone"
    AUTHENTICATED = "authenticated", "Authenticated"
    STAFF = "staff", "Staff"
    GROUP = "group", "Group membership"
    USER_ALLOWLIST = "user_allowlist", "User allowlist"
    USER_DENYLIST = "user_denylist", "User denylist"
    ANONYMOUS_ALLOWLIST = "anonymous_allowlist", "Anonymous allowlist"
    ANONYMOUS_DENYLIST = "anonymous_denylist", "Anonymous denylist"
    PERCENTAGE = "percentage", "Percentage rollout"


class FeatureOverrideScope(models.TextChoices):
    GLOBAL = "global", "Global"
    USER = "user", "User"
    ANONYMOUS = "anonymous", "Anonymous"


class AssignmentSubjectType(models.TextChoices):
    USER = "user", "User"
    ANONYMOUS = "anonymous", "Anonymous"


class FeatureDefinition(models.Model):
    key = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    kind = models.CharField(
        max_length=16,
        choices=FeatureKind.choices,
        default=FeatureKind.BOOLEAN,
    )
    default_value = models.CharField(max_length=64)
    active = models.BooleanField(default=True)
    sticky_assignment = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.key


class FeatureRule(models.Model):
    feature = models.ForeignKey(
        FeatureDefinition,
        on_delete=models.CASCADE,
        related_name="rules",
    )
    name = models.CharField(max_length=120)
    priority = models.PositiveIntegerField(default=100)
    rule_type = models.CharField(
        max_length=32,
        choices=FeatureRuleType.choices,
    )
    value = models.CharField(max_length=64)
    page = models.CharField(max_length=64, blank=True, default="")
    actor_ids = models.JSONField(default=list, blank=True)
    group_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="List of FeatureGroup IDs for GROUP rule type.",
    )
    percentage = models.PositiveSmallIntegerField(null=True, blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["priority", "id"]

    def __str__(self) -> str:
        return f"{self.feature.key}:{self.name}"


class FeatureOverride(models.Model):
    feature = models.ForeignKey(
        FeatureDefinition,
        on_delete=models.CASCADE,
        related_name="overrides",
    )
    scope_type = models.CharField(
        max_length=16,
        choices=FeatureOverrideScope.choices,
        default=FeatureOverrideScope.GLOBAL,
    )
    scope_value = models.CharField(max_length=128, blank=True, default="")
    value = models.CharField(max_length=64)
    note = models.TextField(blank=True, default="")
    enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_feature_overrides",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        unique_together = (("feature", "scope_type", "scope_value"),)
        ordering = ["feature__key", "scope_type", "scope_value"]

    def __str__(self) -> str:
        if self.scope_value:
            return f"{self.feature.key}:{self.scope_type}:{self.scope_value}"
        return f"{self.feature.key}:{self.scope_type}"


class ExperimentAssignment(models.Model):
    feature = models.ForeignKey(
        FeatureDefinition,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    subject_type = models.CharField(
        max_length=16,
        choices=AssignmentSubjectType.choices,
    )
    subject_key = models.CharField(max_length=128)
    page = models.CharField(max_length=64, blank=True, default="")
    value = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("feature", "subject_type", "subject_key", "page"),)
        ordering = ["feature__key", "subject_type", "subject_key", "page"]

    def __str__(self) -> str:
        return (
            f"{self.feature.key}:{self.subject_type}:"
            f"{self.subject_key}:{self.page}"
        )


class FeatureGroup(models.Model):
    """
    A named segment of users for group-based feature flag targeting.

    Unlike Django's built-in auth.Group (which is permissions-focused),
    FeatureGroup is designed specifically for feature rollout segmentation
    and can be managed independently by non-superuser staff.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="feature_groups",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
