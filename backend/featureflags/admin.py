from __future__ import annotations

from functools import partial

from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import NoReverseMatch, path, reverse
from django.utils.html import format_html, format_html_join
from django.views.decorators.csrf import csrf_protect
from simple_history.admin import SimpleHistoryAdmin

from featureflags.admin_services import (
    add_design_tester,
    create_rollout,
    start_rollout,
    stop_rollout,
)
from featureflags.forms import (
    DesignTesterForm,
    FeatureOverrideAdminForm,
    FeatureRuleAdminForm,
    GuidedRolloutForm,
    RolloutAudience,
    StopRolloutForm,
    canonical_value,
    parse_int_values,
    user_label,
    value_choices,
)
from featureflags.models import (
    ExperimentAssignment,
    FeatureDefinition,
    FeatureGroup,
    FeatureOverride,
    FeatureOverrideScope,
    FeatureRule,
    FeatureRuleType,
)
from featureflags.registry import (
    FEATURE_REGISTRY,
    get_feature_title,
    get_rollout_policy,
    is_audience_allowed,
    is_design_flag,
    is_valid_override_value,
)
from featureflags.services import get_effective_default

User = get_user_model()
ROLLOUT_REVIEW_SIGNING_SALT = "featureflags.admin.rollout-review.v1"
ROLLOUT_REVIEW_MAX_AGE_SECONDS = 15 * 60
NO_REVIEW_TOKEN = ""


def _safe_admin_reverse(name: str, *, args=None) -> str:
    try:
        return reverse(f"admin:{name}", args=args)
    except NoReverseMatch:
        # JouTakAdminSite prepends the featureflag routes at startup. Keeping
        # model pages renderable before that hook runs simplifies tests.
        return ""


def _user_labels(user_ids: list[int]) -> list[str]:
    users_by_id = {
        user.pk: user.get_username()
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


def _human_feature_value(feature: FeatureDefinition, value: object) -> str:
    choices = dict(value_choices(feature.key))
    token = canonical_value(value)
    return choices.get(token, token)


def _rule_target_summary(
    rule: FeatureRule,
    *,
    can_view_users: bool = True,
    can_view_groups: bool = True,
) -> str:
    if rule.rule_type == FeatureRuleType.GROUP:
        if not can_view_groups:
            return "Аудитория скрыта: нет права просмотра групп"
        labels = _group_labels(parse_int_values(rule.group_ids or []))
        return ", ".join(labels) if labels else "группа не выбрана"
    if rule.rule_type in {
        FeatureRuleType.USER_ALLOWLIST,
        FeatureRuleType.USER_DENYLIST,
    }:
        if not can_view_users:
            return "Аудитория скрыта: нет права просмотра пользователей"
        labels = _user_labels(parse_int_values(rule.actor_ids or []))
        return ", ".join(labels) if labels else "пользователи не выбраны"
    if rule.rule_type == FeatureRuleType.PERCENTAGE:
        return f"{rule.percentage}% стабильной аудитории"
    return rule.get_rule_type_display()


def _review_summary(cleaned_data: dict) -> dict[str, str]:
    feature = cleaned_data["feature"]
    spec = FEATURE_REGISTRY[feature.key]
    audience = cleaned_data["audience"]
    default = _human_feature_value(feature, get_effective_default(feature))
    if audience == RolloutAudience.GROUP:
        target = ", ".join(
            f"{group.name} ({group.slug}), участников: {group.members.count()}"
            for group in cleaned_data.get("target_groups") or []
        )
    elif audience == RolloutAudience.USERS:
        target = ", ".join(
            user_label(user) for user in cleaned_data.get("target_users") or []
        )
    elif audience == RolloutAudience.PERCENTAGE:
        target = f"{cleaned_data.get('percentage')}% стабильной аудитории"
    else:
        target = dict(RolloutAudience.CHOICES).get(audience, audience)
    effective_overrides, ignored_overrides = _override_counts(feature)
    try:
        sticky_allowed = get_rollout_policy(feature.key).allow_sticky
    except KeyError:
        sticky_allowed = False
    sticky_count = (
        feature.assignments.count()
        if feature.sticky_assignment and sticky_allowed
        else 0
    )
    if audience == RolloutAudience.EVERYONE:
        others = "На выбранной странице отдельной аудитории вне раската нет."
    else:
        others = f"Вне выбранной аудитории базовый результат: {default}."
    precedence_warnings = []
    if effective_overrides:
        precedence_warnings.append(
            "Активные экстренные override применяются раньше раската для "
            f"своей области: {effective_overrides}."
        )
    if ignored_overrides:
        precedence_warnings.append(
            "Override, заблокированные политикой и не влияющие на runtime: "
            f"{ignored_overrides}."
        )
    if sticky_count:
        precedence_warnings.append(
            "Ранее закреплённые назначения применяются раньше раската: "
            f"{sticky_count}."
        )
    return {
        "feature_title": get_feature_title(feature.key),
        "feature_key": feature.key,
        "description": str(spec.get("description") or "—"),
        "visual_impact": str(spec.get("visual_impact") or "—"),
        "value": _human_feature_value(feature, cleaned_data["value"]),
        "page": cleaned_data.get("page") or "все страницы",
        "audience": dict(RolloutAudience.CHOICES).get(audience, audience),
        "target": target,
        "default": default,
        "others": others,
        "precedence_warnings": precedence_warnings,
        "sticky": (
            "Включено: ранее назначенный вариант может сохраниться."
            if spec.get("sticky")
            else "Выключено: закреплённых вариантов нет."
        ),
        "mode": "активный раскат"
        if cleaned_data.get("enabled")
        else "черновик",
    }


def _review_payload(cleaned_data: dict, *, user) -> dict:
    return {
        "user_id": user.pk,
        "feature_id": cleaned_data["feature"].pk,
        "value": cleaned_data["value"],
        "page": cleaned_data.get("page") or "",
        "audience": cleaned_data["audience"],
        "group_ids": sorted(
            group.pk for group in cleaned_data.get("target_groups") or []
        ),
        "user_ids": sorted(
            target.pk for target in cleaned_data.get("target_users") or []
        ),
        "percentage": cleaned_data.get("percentage"),
        "name": cleaned_data.get("name") or "",
        "reason": cleaned_data["reason"],
        "enabled": bool(cleaned_data.get("enabled")),
    }


def _sign_review(cleaned_data: dict, *, user) -> str:
    return signing.dumps(
        _review_payload(cleaned_data, user=user),
        salt=ROLLOUT_REVIEW_SIGNING_SALT,
        compress=True,
    )


def _review_token_is_valid(token: str, cleaned_data: dict, *, user) -> bool:
    if not token:
        return False
    try:
        payload = signing.loads(
            token,
            salt=ROLLOUT_REVIEW_SIGNING_SALT,
            max_age=ROLLOUT_REVIEW_MAX_AGE_SECONDS,
        )
    except signing.BadSignature:
        return False
    return payload == _review_payload(cleaned_data, user=user)


def _override_is_effective(override: FeatureOverride) -> bool:
    """Mirror the runtime policy for persisted emergency overrides."""
    feature = override.feature
    if not feature.active or not is_valid_override_value(
        feature.key, override.value
    ):
        return False
    try:
        guarded_value = get_rollout_policy(feature.key).guarded_value
    except KeyError:
        return False
    return guarded_value is None or canonical_value(
        override.value
    ) != canonical_value(guarded_value)


def _override_counts(feature: FeatureDefinition) -> tuple[int, int]:
    effective = 0
    ignored = 0
    for override in feature.overrides.all():
        if not override.enabled:
            continue
        if _override_is_effective(override):
            effective += 1
        else:
            ignored += 1
    return effective, ignored


def _can_start_rule(user, rule: FeatureRule) -> bool:
    if (
        not user.has_perm("featureflags.change_featurerule")
        or not rule.feature.active
        or rule.feature.key not in FEATURE_REGISTRY
    ):
        return False
    if not is_audience_allowed(rule.feature.key, rule.rule_type):
        return False
    if rule.rule_type == FeatureRuleType.GROUP:
        return user.has_perm("featureflags.view_featuregroup")
    if rule.rule_type in {
        FeatureRuleType.USER_ALLOWLIST,
        FeatureRuleType.USER_DENYLIST,
    }:
        return user.has_perm("auth.view_user")
    if rule.rule_type in {
        FeatureRuleType.AUTHENTICATED,
        FeatureRuleType.PERCENTAGE,
        FeatureRuleType.EVERYONE,
    }:
        return user.has_perm("featureflags.change_featuredefinition")
    return True


def _present_rollout(
    rule: FeatureRule,
    *,
    user,
    can_view_users: bool,
    can_view_groups: bool,
) -> dict:
    feature = rule.feature
    default = _human_feature_value(feature, get_effective_default(feature))
    value = _human_feature_value(feature, rule.value)
    if rule.rule_type in {
        FeatureRuleType.USER_DENYLIST,
        FeatureRuleType.ANONYMOUS_DENYLIST,
    }:
        value = default

    effective_overrides, ignored_overrides = _override_counts(feature)
    warnings = []
    if not feature.active:
        warnings.append(
            "Определение архивировано: runtime игнорирует это правило."
        )
    if effective_overrides:
        warnings.append(
            "Активные экстренные override имеют приоритет для своей "
            f"области: {effective_overrides}."
        )
    if ignored_overrides:
        warnings.append(
            "Сохранённые override, заблокированные политикой реестра и "
            f"не влияющие на runtime: {ignored_overrides}."
        )
    try:
        sticky_allowed = get_rollout_policy(feature.key).allow_sticky
    except KeyError:
        sticky_allowed = False
    sticky_count = (
        feature.assignments.count()
        if feature.active and feature.sticky_assignment and sticky_allowed
        else 0
    )
    if sticky_count:
        warnings.append(
            "Ранее закреплённые назначения имеют приоритет над правилами: "
            f"{sticky_count}."
        )

    if rule.rule_type == FeatureRuleType.EVERYONE:
        others = (
            "На выбранной странице отдельной аудитории вне правила нет; "
            "override и закрепления всё равно применяются раньше."
        )
    else:
        others = (
            "Вне этой аудитории проверяются следующие правила; если ни одно "
            f"не подходит — {default}."
        )
    try:
        feature_title = get_feature_title(feature.key)
    except KeyError:
        feature_title = feature.key
    return {
        "rule": rule,
        "feature_title": feature_title,
        "audience": rule.get_rule_type_display(),
        "target": _rule_target_summary(
            rule,
            can_view_users=can_view_users,
            can_view_groups=can_view_groups,
        ),
        "value": value,
        "page": rule.page or "все страницы",
        "default": default,
        "others": others,
        "warnings": warnings,
        "can_start": _can_start_rule(user, rule),
        "can_stop": bool(
            user.has_perm("featureflags.change_featurerule")
            and feature.active
            and feature.key in FEATURE_REGISTRY
        ),
    }


class RegistryStatusFilter(admin.SimpleListFilter):
    title = "состояние определения"
    parameter_name = "registry_status"

    def lookups(self, request, model_admin):
        choices = [("current", "Объявленные в реестре")]
        if request.user.is_superuser:
            choices.extend((("archived", "Архивные"), ("all", "Все")))
        return tuple(choices)

    def queryset(self, request, queryset):
        if not request.user.is_superuser:
            return queryset.filter(key__in=FEATURE_REGISTRY)
        if self.value() == "all":
            return queryset
        if self.value() == "archived":
            return queryset.exclude(key__in=FEATURE_REGISTRY)
        return queryset.filter(key__in=FEATURE_REGISTRY)


@admin.register(FeatureDefinition)
class FeatureDefinitionAdmin(SimpleHistoryAdmin):
    change_form_template = (
        "admin/featureflags/featuredefinition/change_form.html"
    )
    list_display = (
        "registry_title",
        "key",
        "registry_kind",
        "registry_default",
        "registry_pages",
        "rollout_state",
        "updated_at",
    )
    list_filter = (
        RegistryStatusFilter,
        "active",
        "kind",
        "sticky_assignment",
    )
    search_fields = ("key", "description")
    fields = (
        "key",
        "registry_description",
        "registry_visual_impact",
        "registry_kind",
        "registry_values",
        "registry_default",
        "default_audience_explanation",
        "registry_pages",
        "registry_sticky",
        "active_explanation",
        "override_warning",
        "effective_rollouts",
        "created_at",
        "updated_at",
    )
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def change_view(
        self,
        request,
        object_id,
        form_url="",
        extra_context=None,
    ):
        obj = self.get_object(request, object_id)
        can_access_rollouts = _has_rollout_console_access(request.user)
        context = {
            "is_design_flag": bool(obj and is_design_flag(obj.key)),
            "can_add_rollout": can_access_rollouts
            and request.user.has_perms(
                (
                    "featureflags.add_featurerule",
                    "featureflags.view_featuregroup",
                )
            ),
            "can_add_tester": request.user.has_perms(
                (
                    "featureflags.change_featuregroup",
                    "auth.view_user",
                )
            ),
        }
        context.update(extra_context or {})
        return super().change_view(
            request,
            object_id,
            form_url=form_url,
            extra_context=context,
        )

    def get_queryset(self, request):
        queryset = (
            super()
            .get_queryset(request)
            .prefetch_related("overrides")
            .annotate(
                _enabled_rules_count=Count(
                    "rules", filter=Q(rules__enabled=True), distinct=True
                ),
                _enabled_overrides_count=Count(
                    "overrides",
                    filter=Q(overrides__enabled=True),
                    distinct=True,
                ),
                _assignments_count=Count("assignments", distinct=True),
            )
        )
        if not request.user.is_superuser:
            queryset = queryset.filter(key__in=FEATURE_REGISTRY)
        return queryset

    def _spec(self, obj) -> dict:
        return FEATURE_REGISTRY.get(obj.key, {})

    @admin.display(description="Описание")
    def registry_description(self, obj) -> str:
        return str(
            self._spec(obj).get("description") or obj.description or "—"
        )

    @admin.display(description="Функция")
    def registry_title(self, obj) -> str:
        try:
            return get_feature_title(obj.key)
        except KeyError:
            return obj.key

    @admin.display(description="Что увидит пользователь")
    def registry_visual_impact(self, obj) -> str:
        return str(self._spec(obj).get("visual_impact") or "—")

    @admin.display(description="Тип", ordering="kind")
    def registry_kind(self, obj) -> str:
        return obj.get_kind_display()

    @admin.display(description="Допустимые значения")
    def registry_values(self, obj) -> str:
        return (
            ", ".join(label for _token, label in value_choices(obj.key)) or "—"
        )

    @admin.display(description="Значение по умолчанию")
    def registry_default(self, obj) -> str:
        try:
            return _human_feature_value(obj, get_effective_default(obj))
        except KeyError:
            return obj.default_value

    @admin.display(description="Что увидят остальные")
    def default_audience_explanation(self, obj) -> str:
        return (
            "Если пользователь не попал под override или активное правило, "
            f"он увидит: {self.registry_default(obj)}."
        )

    @admin.display(description="Страницы")
    def registry_pages(self, obj) -> str:
        pages = self._spec(obj).get("pages") or ()
        return (
            ", ".join("все" if page == "*" else page for page in pages) or "—"
        )

    @admin.display(description="Закрепление варианта")
    def registry_sticky(self, obj) -> str:
        enabled = bool(self._spec(obj).get("sticky"))
        assignments = getattr(obj, "_assignments_count", None)
        if assignments is None:
            assignments = obj.assignments.count()
        assignments = int(assignments)
        if assignments:
            return (
                f"{'включено' if enabled else 'выключено'}; "
                f"системных закреплений: {assignments}"
            )
        return "включено" if enabled else "выключено; закреплений нет"

    @admin.display(description="Состояние определения")
    def active_explanation(self, obj) -> str:
        if obj.active:
            return (
                "Активно. Итог зависит от override, правил и значения "
                "по умолчанию."
            )
        return (
            "Архивировано. Это не означает «выключено»: runtime использует "
            "значение по умолчанию из реестра/окружения."
        )

    @admin.display(description="Экстренные исключения")
    def override_warning(self, obj) -> str:
        effective, ignored = _override_counts(obj)
        if not effective and not ignored:
            return "Нет активных override."
        messages_list = []
        if effective:
            messages_list.append(
                "Внимание: runtime-активных override — "
                f"{effective}. Они имеют приоритет над раскатами."
            )
        if ignored:
            messages_list.append(
                "Заблокированных политикой override — "
                f"{ignored}; они не влияют на runtime."
            )
        return format_html_join(
            "",
            '<div class="errornote">{}</div>',
            ((message,) for message in messages_list),
        )

    @admin.display(description="Текущий раскат")
    def effective_rollouts(self, obj) -> str:
        if not obj.active:
            return format_html(
                "Определение архивировано: правила игнорируются; runtime "
                "использует <b>{}</b>.",
                self.registry_default(obj),
            )
        rules = list(obj.rules.filter(enabled=True).order_by("priority", "id"))
        if not rules:
            return format_html(
                "Нет активных правил; используется значение по умолчанию "
                "<b>{}</b>.",
                self.registry_default(obj),
            )
        return format_html_join(
            "",
            "<div><b>{}</b>: {} → {} ({})</div>",
            (
                (
                    rule.name,
                    rule.get_rule_type_display(),
                    _human_feature_value(obj, rule.value),
                    rule.page or "все страницы",
                )
                for rule in rules
            ),
        )

    @admin.display(description="Раскат")
    def rollout_state(self, obj) -> str:
        if not obj.active:
            return (
                f"архивировано; runtime default: {self.registry_default(obj)}"
            )
        rules = int(getattr(obj, "_enabled_rules_count", 0))
        overrides, ignored_overrides = _override_counts(obj)
        default = self.registry_default(obj)
        if overrides:
            return f"⚠ override: {overrides}; default: {default}"
        if ignored_overrides:
            return (
                f"override заблокирован: {ignored_overrides}; "
                f"default: {default}"
            )
        if rules:
            return f"активных раскатов: {rules}; default: {default}"
        return f"по умолчанию: {default}"

    @admin.display(description="Действия")
    def rollout_actions(self, obj) -> str:
        url = _safe_admin_reverse("featureflags_rollout_add")
        if not url or not obj.active or obj.key not in FEATURE_REGISTRY:
            return "—"
        if is_design_flag(obj.key):
            tester_url = _safe_admin_reverse("featureflags_design_tester_add")
            if tester_url:
                return format_html(
                    '<a class="button" href="{}">Добавить тестера</a>',
                    tester_url,
                )
        return format_html(
            '<a class="button" href="{}?feature={}">Новый раскат</a>',
            url,
            obj.pk,
        )


class OperationsOnlyAdminMixin:
    """Keep SQL-shaped pages behind an explicit full-operator role."""

    operations_access_actions = ("view", "change", "delete")
    operations_extra_permissions: tuple[str, ...] = ()

    def _has_operations_access(self, request) -> bool:
        opts = self.model._meta
        permissions = (
            tuple(
                f"{opts.app_label}.{action}_{opts.model_name}"
                for action in self.operations_access_actions
            )
            + self.operations_extra_permissions
        )
        return bool(
            request.user.is_active and request.user.has_perms(permissions)
        )

    def has_module_permission(self, request):
        return self._has_operations_access(request)

    def has_view_permission(self, request, obj=None):
        return bool(
            self._has_operations_access(request)
            and super().has_view_permission(request, obj=obj)
        )

    def has_add_permission(self, request):
        return bool(
            self._has_operations_access(request)
            and super().has_add_permission(request)
        )

    def has_change_permission(self, request, obj=None):
        return bool(
            self._has_operations_access(request)
            and super().has_change_permission(request, obj=obj)
        )

    def has_delete_permission(self, request, obj=None):
        return bool(
            self._has_operations_access(request)
            and super().has_delete_permission(request, obj=obj)
        )


@admin.register(FeatureRule)
class FeatureRuleAdmin(OperationsOnlyAdminMixin, SimpleHistoryAdmin):
    operations_extra_permissions = (
        "auth.view_user",
        "featureflags.view_featuregroup",
    )
    list_display = (
        "feature",
        "name",
        "priority",
        "rule_type",
        "target_summary",
        "human_value",
        "page",
        "enabled",
    )
    list_filter = ("rule_type", "enabled", "page")
    search_fields = ("name", "feature__key")
    list_select_related = ("feature",)
    form = FeatureRuleAdminForm
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Правило",
            {
                "fields": (
                    "feature",
                    "name",
                    "rule_type",
                    "value",
                    "page",
                    "enabled",
                )
            },
        ),
        (
            "Аудитория",
            {
                "fields": (
                    "target_groups",
                    "target_users",
                    "anonymous_ids",
                    "percentage",
                )
            },
        ),
        (
            "Расширенные настройки",
            {
                "classes": ("collapse",),
                "fields": (
                    "priority",
                    "audit_reason",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not request.user.is_superuser:
            queryset = queryset.filter(feature__key__in=FEATURE_REGISTRY)
        return queryset

    def save_model(self, request, obj, form, change):
        obj._history_user = request.user
        obj._change_reason = form.cleaned_data["audit_reason"].strip()[:100]
        obj.full_clean()
        super().save_model(request, obj, form, change)

    @admin.display(description="Значение", ordering="value")
    def human_value(self, obj) -> str:
        return _human_feature_value(obj.feature, obj.value)

    @admin.display(description="Аудитория")
    def target_summary(self, obj) -> str:
        if obj.rule_type == FeatureRuleType.GROUP:
            labels = _group_labels(parse_int_values(obj.group_ids or []))
            return ", ".join(labels) if labels else "группы не выбраны"
        if obj.rule_type in {
            FeatureRuleType.USER_ALLOWLIST,
            FeatureRuleType.USER_DENYLIST,
        }:
            labels = _user_labels(parse_int_values(obj.actor_ids or []))
            return ", ".join(labels) if labels else "пользователи не выбраны"
        if obj.rule_type in {
            FeatureRuleType.ANONYMOUS_ALLOWLIST,
            FeatureRuleType.ANONYMOUS_DENYLIST,
        }:
            values = [str(value) for value in obj.actor_ids or []]
            return (
                ", ".join(values)
                if values
                else "анонимные идентификаторы не выбраны"
            )
        if obj.rule_type == FeatureRuleType.PERCENTAGE:
            return f"{obj.percentage}%"
        return "все подходящие пользователи"


@admin.register(FeatureOverride)
class FeatureOverrideAdmin(OperationsOnlyAdminMixin, SimpleHistoryAdmin):
    operations_access_actions = ("view", "change")
    operations_extra_permissions = ("auth.view_user",)
    list_display = (
        "feature",
        "scope_type",
        "scope_summary",
        "human_value",
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
    form = FeatureOverrideAdminForm
    readonly_fields = ("created_by", "created_at", "updated_at")
    fieldsets = (
        (
            "Экстренное исключение",
            {
                "fields": (
                    "feature",
                    "value",
                    "enabled",
                    "note",
                )
            },
        ),
        (
            "Область действия",
            {
                "fields": (
                    "scope_type",
                    "target_user",
                    "anonymous_scope",
                    "confirm_global",
                )
            },
        ),
        (
            "Аудит",
            {
                "classes": ("collapse",),
                "fields": ("created_by", "created_at", "updated_at"),
            },
        ),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not request.user.is_superuser:
            queryset = queryset.filter(feature__key__in=FEATURE_REGISTRY)
        return queryset

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user
        obj._history_user = request.user
        obj._change_reason = obj.note.strip()[:100]
        obj.full_clean()
        super().save_model(request, obj, form, change)

    @admin.display(description="Значение", ordering="value")
    def human_value(self, obj) -> str:
        return _human_feature_value(obj.feature, obj.value)

    @admin.display(description="Область")
    def scope_summary(self, obj) -> str:
        if obj.scope_type == FeatureOverrideScope.GLOBAL:
            return "Все пользователи"
        if obj.scope_type == FeatureOverrideScope.USER:
            try:
                user = User.objects.get(pk=int(obj.scope_value))
            except (TypeError, ValueError, User.DoesNotExist):
                return f"User #{obj.scope_value}"
            return user_label(user)
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

    def has_module_permission(self, request):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(
            request.user.is_superuser
            and super().has_view_permission(request, obj=obj)
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.concrete_fields)


@admin.register(FeatureGroup)
class FeatureGroupAdmin(OperationsOnlyAdminMixin, admin.ModelAdmin):
    operations_extra_permissions = ("auth.view_user",)
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

    @admin.display(description="Участники", ordering="_member_count")
    def member_count(self, obj) -> int:
        return int(getattr(obj, "_member_count", 0))


def _require_permission(request: HttpRequest, permission: str) -> None:
    if not request.user.has_perm(permission):
        raise PermissionDenied


def _require_permissions(request: HttpRequest, *permissions: str) -> None:
    if not request.user.has_perms(permissions):
        raise PermissionDenied


def _has_rollout_console_access(user) -> bool:
    return bool(
        user.has_perm("featureflags.view_featuredefinition")
        and (
            user.has_perm("featureflags.view_featurerule")
            or user.has_perm("featureflags.change_featurerule")
        )
    )


def _require_rollout_console_access(request: HttpRequest) -> None:
    if not _has_rollout_console_access(request.user):
        raise PermissionDenied


def _rollout_context(admin_site, request: HttpRequest, **extra) -> dict:
    context = {
        **admin_site.each_context(request),
        "opts": FeatureDefinition._meta,
        "has_view_permission": _has_rollout_console_access(request.user),
        "has_add_permission": _has_rollout_console_access(request.user)
        and request.user.has_perms(
            (
                "featureflags.add_featurerule",
                "featureflags.view_featuregroup",
            )
        ),
        "rollout_index_url": _safe_admin_reverse("featureflags_rollout_index"),
        "rollout_add_url": _safe_admin_reverse("featureflags_rollout_add"),
        "design_tester_url": _safe_admin_reverse(
            "featureflags_design_tester_add"
        ),
        "definition_list_url": _safe_admin_reverse(
            "featureflags_featuredefinition_changelist"
        ),
    }
    context.update(extra)
    return context


def rollout_index_view(request: HttpRequest, *, admin_site) -> HttpResponse:
    _require_rollout_console_access(request)
    can_view_users = request.user.has_perm("auth.view_user")
    can_view_groups = request.user.has_perm("featureflags.view_featuregroup")
    rules = (
        FeatureRule.objects.filter(feature__key__in=FEATURE_REGISTRY)
        .select_related("feature")
        .prefetch_related(
            "feature__overrides",
            "feature__assignments",
        )
    )
    active_rules = list(
        rules.filter(enabled=True).order_by(
            "feature__key", "page", "priority", "id"
        )
    )
    active_rollouts = [
        _present_rollout(
            rule,
            user=request.user,
            can_view_users=can_view_users,
            can_view_groups=can_view_groups,
        )
        for rule in active_rules
    ]
    disabled_rules = list(rules.filter(enabled=False).order_by("-updated_at"))
    draft_rollouts = []
    for rule in disabled_rules:
        created = rule.history.order_by("history_date", "history_id").first()
        if created and not created.enabled:
            draft_rollouts.append(
                _present_rollout(
                    rule,
                    user=request.user,
                    can_view_users=can_view_users,
                    can_view_groups=can_view_groups,
                )
            )
    recent_history = FeatureRule.history.select_related(
        "feature", "history_user"
    ).order_by("-history_date")
    recent_history = recent_history.filter(feature__key__in=FEATURE_REGISTRY)
    recent_history = recent_history[:30]
    context = _rollout_context(
        admin_site,
        request,
        title="Раскаты фича-флагов",
        active_rollouts=active_rollouts,
        draft_rollouts=draft_rollouts,
        recent_history=recent_history,
        can_stop=request.user.has_perm("featureflags.change_featurerule"),
        can_add_tester=request.user.has_perm(
            "featureflags.change_featuregroup"
        )
        and request.user.has_perm("auth.view_user"),
    )
    return TemplateResponse(
        request, "admin/featureflags/rollout_index.html", context
    )


@csrf_protect
def rollout_add_view(request: HttpRequest, *, admin_site) -> HttpResponse:
    _require_rollout_console_access(request)
    _require_permissions(
        request,
        "featureflags.add_featurerule",
        "featureflags.view_featuregroup",
    )
    initial = {}
    requested_feature = request.GET.get("feature")
    if requested_feature:
        initial["feature"] = requested_feature
    create_requested = request.method == "POST" and "_create" in request.POST
    form = GuidedRolloutForm(
        request.POST or None,
        initial=initial,
        request_user=request.user,
        require_confirmation=create_requested,
    )
    if request.method == "POST" and form.is_valid():
        if not create_requested:
            review_token = _sign_review(
                form.cleaned_data,
                user=request.user,
            )
            context = _rollout_context(
                admin_site,
                request,
                title="Проверка раската",
                form=form,
                media=form.media,
                review=True,
                review_summary=_review_summary(form.cleaned_data),
                review_token=review_token,
            )
            return TemplateResponse(
                request,
                "admin/featureflags/rollout_form.html",
                context,
            )
        if not _review_token_is_valid(
            request.POST.get("review_token", ""),
            form.cleaned_data,
            user=request.user,
        ):
            form.add_error(
                None,
                "Параметры изменились или проверка устарела. "
                "Проверьте итог ещё раз.",
            )
        else:
            try:
                rule = create_rollout(
                    cleaned_data=form.cleaned_data, user=request.user
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                if getattr(rule, "_rollout_was_created", True):
                    admin_site._registry[FeatureRule].log_addition(
                        request,
                        rule,
                        "Создано через безопасную форму раската.",
                    )
                    messages.success(request, f"Раскат «{rule.name}» создан.")
                else:
                    messages.info(
                        request,
                        f"Черновик «{rule.name}» уже был создан; "
                        "повтор не добавлен.",
                    )
                return redirect("admin:featureflags_rollout_index")
    summary = None
    review_token = NO_REVIEW_TOKEN
    confirmation_only_error = set(form.errors) == {"confirm_rollout"}
    submitted_review_token = request.POST.get("review_token", "")
    if (
        create_requested
        and confirmation_only_error
        and _review_token_is_valid(
            submitted_review_token,
            form.cleaned_data,
            user=request.user,
        )
    ):
        summary = _review_summary(form.cleaned_data)
        review_token = submitted_review_token
    context = _rollout_context(
        admin_site,
        request,
        title="Новый раскат",
        form=form,
        media=form.media,
        review=bool(summary),
        review_summary=summary,
        review_token=review_token,
    )
    return TemplateResponse(
        request, "admin/featureflags/rollout_form.html", context
    )


@csrf_protect
def rollout_stop_view(
    request: HttpRequest, rule_id: int, *, admin_site
) -> HttpResponse:
    _require_rollout_console_access(request)
    _require_permission(request, "featureflags.change_featurerule")
    if request.method != "POST":
        return HttpResponseNotAllowed(("POST",))
    form = StopRolloutForm(request.POST)
    if not form.is_valid():
        messages.error(
            request, "Укажите причину остановки (минимум 5 символов)."
        )
        return redirect("admin:featureflags_rollout_index")
    try:
        rule = stop_rollout(
            rule_id=rule_id,
            user=request.user,
            reason=form.cleaned_data["reason"],
        )
    except (FeatureRule.DoesNotExist, ValidationError) as exc:
        detail = (
            "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
        )
        messages.error(request, detail)
    else:
        admin_site._registry[FeatureRule].log_change(
            request, rule, "Раскат остановлен без удаления истории."
        )
        messages.success(request, f"Раскат «{rule.name}» остановлен.")
    return redirect("admin:featureflags_rollout_index")


@csrf_protect
def rollout_start_view(
    request: HttpRequest, rule_id: int, *, admin_site
) -> HttpResponse:
    _require_rollout_console_access(request)
    _require_permission(request, "featureflags.change_featurerule")
    if request.method != "POST":
        return HttpResponseNotAllowed(("POST",))
    form = StopRolloutForm(request.POST)
    if not form.is_valid():
        messages.error(
            request, "Укажите причину запуска (минимум 5 символов)."
        )
        return redirect("admin:featureflags_rollout_index")
    try:
        rule = start_rollout(
            rule_id=rule_id,
            user=request.user,
            reason=form.cleaned_data["reason"],
        )
    except (FeatureRule.DoesNotExist, ValidationError) as exc:
        detail = (
            "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
        )
        messages.error(request, detail)
    else:
        admin_site._registry[FeatureRule].log_change(
            request, rule, "Черновик раската запущен."
        )
        messages.success(request, f"Раскат «{rule.name}» запущен.")
    return redirect("admin:featureflags_rollout_index")


@csrf_protect
def design_tester_add_view(
    request: HttpRequest, *, admin_site
) -> HttpResponse:
    _require_permissions(
        request,
        "featureflags.change_featuregroup",
        "auth.view_user",
    )
    form = DesignTesterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            add_design_tester(
                target_user=form.cleaned_data["user"],
                user=request.user,
                reason=form.cleaned_data["reason"],
            )
        except FeatureGroup.DoesNotExist:
            form.add_error(
                None,
                "Группа website-design-testers отсутствует. "
                "Запустите sync_feature_registry.",
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(
                request,
                f"{user_label(form.cleaned_data['user'])} добавлен "
                "в дизайн-тестеры.",
            )
            return redirect("admin:featureflags_design_tester_add")
    context = _rollout_context(
        admin_site,
        request,
        title="Добавить дизайн-тестера",
        form=form,
        design_tester_return_url=(
            _safe_admin_reverse("featureflags_rollout_index")
            if _has_rollout_console_access(request.user)
            else reverse("admin:index")
        ),
    )
    return TemplateResponse(
        request, "admin/featureflags/design_tester_form.html", context
    )


def get_rollout_admin_urls(admin_site) -> list:
    """Routes to prepend in :meth:`JouTakAdminSite.get_urls`."""
    return [
        path(
            "featureflags/rollouts/",
            admin_site.admin_view(
                partial(rollout_index_view, admin_site=admin_site)
            ),
            name="featureflags_rollout_index",
        ),
        path(
            "featureflags/rollouts/new/",
            admin_site.admin_view(
                partial(rollout_add_view, admin_site=admin_site)
            ),
            name="featureflags_rollout_add",
        ),
        path(
            "featureflags/rollouts/<int:rule_id>/stop/",
            admin_site.admin_view(
                partial(rollout_stop_view, admin_site=admin_site)
            ),
            name="featureflags_rollout_stop",
        ),
        path(
            "featureflags/rollouts/<int:rule_id>/start/",
            admin_site.admin_view(
                partial(rollout_start_view, admin_site=admin_site)
            ),
            name="featureflags_rollout_start",
        ),
        path(
            "featureflags/design-testers/add/",
            admin_site.admin_view(
                partial(design_tester_add_view, admin_site=admin_site)
            ),
            name="featureflags_design_tester_add",
        ),
    ]
