from __future__ import annotations

from django.contrib import admin
from django.db.models import Count

from featureflags.models import (
    ExperimentAssignment,
    FeatureDefinition,
    FeatureOverride,
    FeatureRule,
)


class FeatureRuleInline(admin.TabularInline):
    model = FeatureRule
    extra = 0
    fields = (
        "name",
        "priority",
        "rule_type",
        "value",
        "page",
        "actor_ids",
        "percentage",
        "enabled",
    )
    ordering = ("priority", "id")


class FeatureOverrideInline(admin.TabularInline):
    model = FeatureOverride
    extra = 0
    fields = (
        "scope_type",
        "scope_value",
        "value",
        "enabled",
        "note",
        "created_by",
    )
    readonly_fields = ("created_by", "created_at", "updated_at")
    ordering = ("scope_type", "scope_value")


@admin.register(FeatureDefinition)
class FeatureDefinitionAdmin(admin.ModelAdmin):
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
class FeatureRuleAdmin(admin.ModelAdmin):
    list_display = (
        "feature",
        "name",
        "priority",
        "rule_type",
        "value",
        "page",
        "enabled",
    )
    list_filter = ("rule_type", "enabled", "page")
    search_fields = ("name", "feature__key")
    list_select_related = ("feature",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(FeatureOverride)
class FeatureOverrideAdmin(admin.ModelAdmin):
    list_display = (
        "feature",
        "scope_type",
        "scope_value",
        "value",
        "enabled",
        "created_by",
        "created_at",
        "updated_at",
    )
    list_filter = ("scope_type", "enabled")
    search_fields = ("feature__key", "scope_value", "note")
    list_select_related = ("feature", "created_by")
    readonly_fields = ("created_by", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


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
    readonly_fields = ("created_at", "updated_at")
