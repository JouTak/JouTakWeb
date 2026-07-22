from __future__ import annotations

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords


class FeatureKind(models.TextChoices):
    BOOLEAN = "boolean", "Булевый"
    VARIANT = "variant", "Вариантный"


class FeatureRuleType(models.TextChoices):
    EVERYONE = "everyone", "Все"
    AUTHENTICATED = "authenticated", "Авторизованные"
    STAFF = "staff", "Персонал"
    GROUP = "group", "Группа"
    USER_ALLOWLIST = "user_allowlist", "Белый список (пользователи)"
    USER_DENYLIST = "user_denylist", "Чёрный список (пользователи)"
    ANONYMOUS_ALLOWLIST = "anonymous_allowlist", "Белый список (анонимы)"
    ANONYMOUS_DENYLIST = "anonymous_denylist", "Чёрный список (анонимы)"
    PERCENTAGE = "percentage", "Процентный раскат"


class FeatureOverrideScope(models.TextChoices):
    GLOBAL = "global", "Глобальный"
    USER = "user", "Пользователь"
    ANONYMOUS = "anonymous", "Аноним"


class AssignmentSubjectType(models.TextChoices):
    USER = "user", "Пользователь"
    ANONYMOUS = "anonymous", "Аноним"


class FeatureDefinition(models.Model):
    key = models.CharField("ключ", max_length=100, unique=True)
    description = models.TextField("описание", blank=True, default="")
    kind = models.CharField(
        "тип",
        max_length=16,
        choices=FeatureKind.choices,
        default=FeatureKind.BOOLEAN,
    )
    default_value = models.CharField("значение по умолчанию", max_length=64)
    active = models.BooleanField("активен", default=True)
    sticky_assignment = models.BooleanField(
        "закреплённое назначение", default=False
    )
    created_at = models.DateTimeField("создан", auto_now_add=True)
    updated_at = models.DateTimeField("обновлён", auto_now=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["key"]
        verbose_name = "фича-флаг"
        verbose_name_plural = "фича-флаги"

    def __str__(self) -> str:
        return self.key


class FeatureRule(models.Model):
    feature = models.ForeignKey(
        FeatureDefinition,
        on_delete=models.CASCADE,
        related_name="rules",
        verbose_name="фича-флаг",
    )
    name = models.CharField("название", max_length=120)
    priority = models.PositiveIntegerField("приоритет", default=100)
    rule_type = models.CharField(
        "тип правила",
        max_length=32,
        choices=FeatureRuleType.choices,
    )
    value = models.CharField("значение", max_length=64)
    page = models.CharField("страница", max_length=64, blank=True, default="")
    actor_ids = models.JSONField("ID субъектов", default=list, blank=True)
    group_ids = models.JSONField(
        "ID групп",
        default=list,
        blank=True,
        help_text="Список ID FeatureGroup для правила типа «Группа».",
    )
    percentage = models.PositiveSmallIntegerField(
        "процент", null=True, blank=True
    )
    enabled = models.BooleanField("включено", default=True)
    created_at = models.DateTimeField("создано", auto_now_add=True)
    updated_at = models.DateTimeField("обновлено", auto_now=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["priority", "id"]
        verbose_name = "правило"
        verbose_name_plural = "правила"

    def __str__(self) -> str:
        return f"{self.feature.key}:{self.name}"


class FeatureOverride(models.Model):
    feature = models.ForeignKey(
        FeatureDefinition,
        on_delete=models.CASCADE,
        related_name="overrides",
        verbose_name="фича-флаг",
    )
    scope_type = models.CharField(
        "область",
        max_length=16,
        choices=FeatureOverrideScope.choices,
        default=FeatureOverrideScope.GLOBAL,
    )
    scope_value = models.CharField(
        "значение области", max_length=128, blank=True, default=""
    )
    value = models.CharField("значение", max_length=64)
    note = models.TextField("заметка", blank=True, default="")
    enabled = models.BooleanField("включено", default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_feature_overrides",
        verbose_name="создано пользователем",
    )
    created_at = models.DateTimeField("создано", auto_now_add=True)
    updated_at = models.DateTimeField("обновлено", auto_now=True)
    history = HistoricalRecords()

    class Meta:
        unique_together = (("feature", "scope_type", "scope_value"),)
        ordering = ["feature__key", "scope_type", "scope_value"]
        verbose_name = "переопределение"
        verbose_name_plural = "переопределения"

    def __str__(self) -> str:
        if self.scope_value:
            return f"{self.feature.key}:{self.scope_type}:{self.scope_value}"
        return f"{self.feature.key}:{self.scope_type}"


class ExperimentAssignment(models.Model):
    feature = models.ForeignKey(
        FeatureDefinition,
        on_delete=models.CASCADE,
        related_name="assignments",
        verbose_name="фича-флаг",
    )
    subject_type = models.CharField(
        "тип субъекта",
        max_length=16,
        choices=AssignmentSubjectType.choices,
    )
    subject_key = models.CharField("ключ субъекта", max_length=128)
    page = models.CharField("страница", max_length=64, blank=True, default="")
    value = models.CharField("значение", max_length=64)
    created_at = models.DateTimeField("создано", auto_now_add=True)
    updated_at = models.DateTimeField("обновлено", auto_now=True)

    class Meta:
        unique_together = (("feature", "subject_type", "subject_key", "page"),)
        ordering = ["feature__key", "subject_type", "subject_key", "page"]
        verbose_name = "назначение эксперимента"
        verbose_name_plural = "назначения экспериментов"

    def __str__(self) -> str:
        return (
            f"{self.feature.key}:{self.subject_type}:"
            f"{self.subject_key}:{self.page}"
        )


class FeatureGroup(models.Model):
    """
    Именованный сегмент пользователей для group-based таргетирования
    фича-флагов. Управляется отдельно от Django auth.Group.
    """

    name = models.CharField("название", max_length=100, unique=True)
    slug = models.SlugField("слаг", max_length=100, unique=True)
    description = models.TextField("описание", blank=True, default="")
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="feature_groups",
        verbose_name="участники",
    )
    created_at = models.DateTimeField("создана", auto_now_add=True)
    updated_at = models.DateTimeField("обновлена", auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "группа таргетирования"
        verbose_name_plural = "группы таргетирования"

    def __str__(self) -> str:
        return self.name
