from __future__ import annotations

import re

from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import Count
from simple_history.admin import SimpleHistoryAdmin

from featureflags.models import (
    ExperimentAssignment,
    FeatureDefinition,
    FeatureGroup,
    FeatureOverride,
    FeatureOverrideScope,
    FeatureRule,
    FeatureRuleType,
)

User = get_user_model()


def _unique_text_values(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        raw = str(value).strip()
        if raw and raw not in seen:
            seen.add(raw)
            result.append(raw)
    return result


def _split_text_values(raw: str | None) -> list[str]:
    if not raw:
        return []
    return _unique_text_values(re.split(r"[\n,]+", raw))


def _parse_int_values(values) -> list[int]:
    parsed: list[int] = []
    seen: set[int] = set()
    for value in values:
        try:
            parsed_value = int(value)
        except (TypeError, ValueError):
            continue
        if parsed_value not in seen:
            seen.add(parsed_value)
            parsed.append(parsed_value)
    return parsed


def _user_label(user) -> str:
    if getattr(user, "email", ""):
        return f"{user.get_username()} <{user.email}>"
    return user.get_username()


def _user_labels(user_ids: list[int]) -> list[str]:
    users_by_id = {
        user.pk: _user_label(user)
        for user in User.objects.filter(pk__in=user_ids)
    }
    return [
        users_by_id.get(user_id, f"User #{user_id}") for user_id in user_ids
    ]


def _group_labels(group_ids: list[int]) -> list[str]:
    groups_by_id = {
        group.pk: f"{group.name} ({group.slug})"
        for group in FeatureGroup.objects.filter(pk__in=group_ids)
    }
    return [
        groups_by_id.get(group_id, f"Group #{group_id}")
        for group_id in group_ids
    ]


class UserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj) -> str:
        return _user_label(obj)


class UserMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj) -> str:
        return _user_label(obj)


class FeatureRuleAdminForm(forms.ModelForm):
    target_users = UserMultipleChoiceField(
        queryset=User.objects.order_by("username", "email"),
        required=False,
        label="Пользователи",
        widget=admin.widgets.FilteredSelectMultiple("Пользователи", False),
        help_text=(
            "Используется для правил типа allow/deny list по пользователям."
        ),
    )
    anonymous_ids = forms.CharField(
        required=False,
        label="Анонимные идентификаторы",
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Один идентификатор на строку или через запятую.",
    )
    target_groups = forms.ModelMultipleChoiceField(
        queryset=FeatureGroup.objects.order_by("name"),
        required=False,
        label="Группы",
        widget=admin.widgets.FilteredSelectMultiple("Группы", False),
        help_text="Используется для group-правил.",
    )

    class Meta:
        model = FeatureRule
        fields = (
            "feature",
            "name",
            "priority",
            "rule_type",
            "value",
            "page",
            "percentage",
            "enabled",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            return

        if self.instance.rule_type in {
            FeatureRuleType.USER_ALLOWLIST,
            FeatureRuleType.USER_DENYLIST,
        }:
            self.fields["target_users"].initial = User.objects.filter(
                pk__in=_parse_int_values(self.instance.actor_ids or [])
            )
        elif self.instance.rule_type in {
            FeatureRuleType.ANONYMOUS_ALLOWLIST,
            FeatureRuleType.ANONYMOUS_DENYLIST,
        }:
            self.fields["anonymous_ids"].initial = "\n".join(
                _unique_text_values(self.instance.actor_ids or [])
            )
        elif self.instance.rule_type == FeatureRuleType.GROUP:
            self.fields["target_groups"].initial = FeatureGroup.objects.filter(
                pk__in=_parse_int_values(self.instance.group_ids or [])
            )

    def clean(self):
        cleaned_data = super().clean()
        rule_type = cleaned_data.get("rule_type")

        if rule_type == FeatureRuleType.GROUP:
            if not cleaned_data.get("target_groups"):
                self.add_error(
                    "target_groups",
                    "Выберите хотя бы одну группу.",
                )
        elif rule_type in {
            FeatureRuleType.USER_ALLOWLIST,
            FeatureRuleType.USER_DENYLIST,
        }:
            if not cleaned_data.get("target_users"):
                self.add_error(
                    "target_users",
                    "Выберите хотя бы одного пользователя.",
                )
        elif rule_type in {
            FeatureRuleType.ANONYMOUS_ALLOWLIST,
            FeatureRuleType.ANONYMOUS_DENYLIST,
        }:
            if not _split_text_values(cleaned_data.get("anonymous_ids")):
                self.add_error(
                    "anonymous_ids",
                    "Добавьте хотя бы один анонимный идентификатор.",
                )
        elif rule_type == FeatureRuleType.PERCENTAGE:
            if cleaned_data.get("percentage") is None:
                self.add_error("percentage", "Укажите процент раската.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        rule_type = self.cleaned_data.get("rule_type")

        if rule_type == FeatureRuleType.GROUP:
            instance.group_ids = [
                group.pk
                for group in self.cleaned_data.get("target_groups") or []
            ]
            instance.actor_ids = []
        elif rule_type in {
            FeatureRuleType.USER_ALLOWLIST,
            FeatureRuleType.USER_DENYLIST,
        }:
            instance.actor_ids = [
                str(user.pk)
                for user in self.cleaned_data.get("target_users") or []
            ]
            instance.group_ids = []
        elif rule_type in {
            FeatureRuleType.ANONYMOUS_ALLOWLIST,
            FeatureRuleType.ANONYMOUS_DENYLIST,
        }:
            instance.actor_ids = _split_text_values(
                self.cleaned_data.get("anonymous_ids")
            )
            instance.group_ids = []
        else:
            instance.actor_ids = []
            instance.group_ids = []

        if commit:
            instance.save()
            self.save_m2m()
        return instance


class FeatureOverrideAdminForm(forms.ModelForm):
    target_user = UserChoiceField(
        queryset=User.objects.order_by("username", "email"),
        required=False,
        label="Пользователь",
        help_text="Используется, когда область переопределения = user.",
    )
    anonymous_scope = forms.CharField(
        required=False,
        label="Анонимный идентификатор",
        widget=forms.TextInput(),
        help_text="Используется, когда область переопределения = anonymous.",
    )

    class Meta:
        model = FeatureOverride
        fields = (
            "feature",
            "scope_type",
            "value",
            "enabled",
            "note",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            return

        if self.instance.scope_type == FeatureOverrideScope.USER:
            try:
                self.fields["target_user"].initial = User.objects.get(
                    pk=int(self.instance.scope_value)
                )
            except (TypeError, ValueError, User.DoesNotExist):
                self.fields["target_user"].initial = None
        elif self.instance.scope_type == FeatureOverrideScope.ANONYMOUS:
            self.fields["anonymous_scope"].initial = self.instance.scope_value

    def clean(self):
        cleaned_data = super().clean()
        scope_type = cleaned_data.get("scope_type")

        if scope_type == FeatureOverrideScope.USER:
            if not cleaned_data.get("target_user"):
                self.add_error("target_user", "Выберите пользователя.")
        elif scope_type == FeatureOverrideScope.ANONYMOUS:
            if not str(cleaned_data.get("anonymous_scope") or "").strip():
                self.add_error(
                    "anonymous_scope",
                    "Укажите анонимный идентификатор.",
                )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        scope_type = self.cleaned_data.get("scope_type")

        if scope_type == FeatureOverrideScope.USER:
            user = self.cleaned_data.get("target_user")
            instance.scope_value = str(user.pk) if user else ""
        elif scope_type == FeatureOverrideScope.ANONYMOUS:
            instance.scope_value = str(
                self.cleaned_data.get("anonymous_scope") or ""
            ).strip()
        else:
            instance.scope_value = ""

        if commit:
            instance.save()
            self.save_m2m()
        return instance


class FeatureRuleInline(admin.TabularInline):
    model = FeatureRule
    form = FeatureRuleAdminForm
    extra = 0
    fields = (
        "name",
        "priority",
        "rule_type",
        "value",
        "page",
        "target_users",
        "anonymous_ids",
        "target_groups",
        "percentage",
        "enabled",
    )
    ordering = ("priority", "id")


class FeatureOverrideInline(admin.TabularInline):
    model = FeatureOverride
    form = FeatureOverrideAdminForm
    extra = 0
    fields = (
        "scope_type",
        "target_user",
        "anonymous_scope",
        "value",
        "enabled",
        "note",
        "created_by",
    )
    readonly_fields = ("created_by", "created_at", "updated_at")
    ordering = ("scope_type", "scope_value")


@admin.register(FeatureDefinition)
class FeatureDefinitionAdmin(SimpleHistoryAdmin):
    list_display = (
        "key",
        "kind",
        "default_value",
        "active",
        "sticky_assignment",
        "rules_count",
        "overrides_count",
        "assignments_count",
        "updated_at",
    )
    list_filter = ("kind", "active", "sticky_assignment")
    search_fields = ("key", "description")
    readonly_fields = ("created_at", "updated_at")
    inlines = (FeatureRuleInline, FeatureOverrideInline)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            _rules_count=Count("rules", distinct=True),
            _overrides_count=Count("overrides", distinct=True),
            _assignments_count=Count("assignments", distinct=True),
        )

    @admin.display(description="Rules", ordering="_rules_count")
    def rules_count(self, obj) -> int:
        return int(getattr(obj, "_rules_count", 0))

    @admin.display(description="Overrides", ordering="_overrides_count")
    def overrides_count(self, obj) -> int:
        return int(getattr(obj, "_overrides_count", 0))

    @admin.display(description="Assignments", ordering="_assignments_count")
    def assignments_count(self, obj) -> int:
        return int(getattr(obj, "_assignments_count", 0))


@admin.register(FeatureRule)
class FeatureRuleAdmin(SimpleHistoryAdmin):
    list_display = (
        "feature",
        "name",
        "priority",
        "rule_type",
        "target_summary",
        "value",
        "page",
        "enabled",
    )
    list_filter = ("rule_type", "enabled", "page")
    search_fields = ("name", "feature__key")
    list_select_related = ("feature",)
    autocomplete_fields = ("feature",)
    form = FeatureRuleAdminForm
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Targets")
    def target_summary(self, obj) -> str:
        if obj.rule_type == FeatureRuleType.GROUP:
            labels = _group_labels(_parse_int_values(obj.group_ids or []))
            return ", ".join(labels) if labels else "no groups"
        if obj.rule_type in {
            FeatureRuleType.USER_ALLOWLIST,
            FeatureRuleType.USER_DENYLIST,
        }:
            labels = _user_labels(_parse_int_values(obj.actor_ids or []))
            return ", ".join(labels) if labels else "no users"
        if obj.rule_type in {
            FeatureRuleType.ANONYMOUS_ALLOWLIST,
            FeatureRuleType.ANONYMOUS_DENYLIST,
        }:
            values = _unique_text_values(obj.actor_ids or [])
            return ", ".join(values) if values else "no anonymous ids"
        return "all users"


@admin.register(FeatureOverride)
class FeatureOverrideAdmin(SimpleHistoryAdmin):
    list_display = (
        "feature",
        "scope_type",
        "scope_summary",
        "value",
        "enabled",
        "created_by",
        "created_at",
        "updated_at",
    )
    list_filter = ("scope_type", "enabled")
    search_fields = (
        "feature__key",
        "scope_value",
        "note",
        "created_by__username",
        "created_by__email",
    )
    list_select_related = ("feature", "created_by")
    autocomplete_fields = ("feature",)
    form = FeatureOverrideAdminForm
    readonly_fields = ("created_by", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Scope")
    def scope_summary(self, obj) -> str:
        if obj.scope_type == FeatureOverrideScope.GLOBAL:
            return "Everyone"
        if obj.scope_type == FeatureOverrideScope.USER:
            try:
                user = User.objects.get(pk=int(obj.scope_value))
            except (TypeError, ValueError, User.DoesNotExist):
                return f"User #{obj.scope_value}"
            return _user_label(user)
        if obj.scope_type == FeatureOverrideScope.ANONYMOUS:
            return obj.scope_value or "anonymous"
        return obj.scope_value or obj.scope_type


@admin.register(ExperimentAssignment)
class ExperimentAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "feature",
        "subject_type",
        "subject_key",
        "page",
        "value",
        "updated_at",
    )
    list_filter = ("subject_type", "page")
    search_fields = ("feature__key", "subject_key", "value")
    list_select_related = ("feature",)
    autocomplete_fields = ("feature",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(FeatureGroup)
class FeatureGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "member_count", "created_at")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("members",)
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(_member_count=Count("members", distinct=True))
        )

    @admin.display(description="Members", ordering="_member_count")
    def member_count(self, obj) -> int:
        return int(getattr(obj, "_member_count", 0))
