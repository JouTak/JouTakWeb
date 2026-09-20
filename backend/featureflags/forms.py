from __future__ import annotations

import json
import re
from collections.abc import Iterable

from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q

from featureflags.models import (
    FeatureDefinition,
    FeatureGroup,
    FeatureOverride,
    FeatureOverrideScope,
    FeatureRule,
    FeatureRuleType,
)
from featureflags.registry import (
    FEATURE_REGISTRY,
    canonical_variant_token,
    get_allowed_audiences,
    get_feature_title,
    get_required_group_slug,
    get_rollout_policy,
    get_variant_choices,
    is_audience_allowed,
    is_design_flag,
)
from featureflags.services import get_effective_default

User = get_user_model()


class RolloutAudience:
    GROUP = "group"
    USERS = "users"
    STAFF = "staff"
    AUTHENTICATED = "authenticated"
    PERCENTAGE = "percentage"
    EVERYONE = "everyone"

    CHOICES = (
        (GROUP, "Группа тестировщиков"),
        (USERS, "Выбранные пользователи"),
        (STAFF, "Сотрудники"),
        (AUTHENTICATED, "Все авторизованные"),
        (PERCENTAGE, "Процент аудитории"),
        (EVERYONE, "Все посетители"),
    )

    DANGEROUS = frozenset({AUTHENTICATED, PERCENTAGE, EVERYONE})


AUDIENCE_TO_RULE_TYPE = {
    RolloutAudience.GROUP: FeatureRuleType.GROUP,
    RolloutAudience.USERS: FeatureRuleType.USER_ALLOWLIST,
    RolloutAudience.STAFF: FeatureRuleType.STAFF,
    RolloutAudience.AUTHENTICATED: FeatureRuleType.AUTHENTICATED,
    RolloutAudience.PERCENTAGE: FeatureRuleType.PERCENTAGE,
    RolloutAudience.EVERYONE: FeatureRuleType.EVERYONE,
}


def _unique_text_values(values: Iterable[object]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        raw = str(value).strip()
        if raw and raw not in seen:
            seen.add(raw)
            result.append(raw)
    return result


def split_text_values(raw: str | None) -> list[str]:
    if not raw:
        return []
    return _unique_text_values(re.split(r"[\n,]+", raw))


def parse_int_values(values: Iterable[object]) -> list[int]:
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


def user_label(user) -> str:
    if getattr(user, "email", ""):
        return f"{user.get_username()} <{user.email}>"
    return user.get_username()


def canonical_value(value: object) -> str:
    return canonical_variant_token(value)


def value_choices(
    feature_key: str | None,
    *,
    include_guarded: bool = True,
) -> tuple[tuple[str, str], ...]:
    choices = get_variant_choices(feature_key or "")
    if include_guarded or not feature_key:
        return choices
    try:
        guarded = get_rollout_policy(feature_key).guarded_value
    except KeyError:
        return ()
    if guarded is None:
        return choices
    guarded_token = canonical_value(guarded)
    return tuple(choice for choice in choices if choice[0] != guarded_token)


def page_choices(feature_key: str | None) -> tuple[tuple[str, str], ...]:
    """Return DB-safe page choices; registry `*` is stored as blank."""
    spec = FEATURE_REGISTRY.get(feature_key or "")
    if spec is None:
        return ()
    result: list[tuple[str, str]] = []
    for page in spec["pages"]:
        choice = ("", "Все страницы") if page == "*" else (page, page)
        if choice not in result:
            result.append(choice)
    return tuple(result)


def _selected_feature(form: forms.Form) -> FeatureDefinition | None:
    field_name = form.add_prefix("feature")
    feature_pk = form.data.get(field_name) if form.is_bound else None
    if not feature_pk:
        feature = form.initial.get("feature")
        if isinstance(feature, FeatureDefinition):
            return feature
        feature_pk = getattr(feature, "pk", feature)
    if not feature_pk and getattr(form, "instance", None):
        feature_pk = getattr(form.instance, "feature_id", None)
    if not feature_pk:
        return None
    try:
        return FeatureDefinition.objects.get(pk=feature_pk)
    except (TypeError, ValueError, FeatureDefinition.DoesNotExist):
        return None


def _configure_registry_fields(
    form: forms.Form,
    *,
    include_guarded: bool = True,
) -> None:
    feature = _selected_feature(form)
    feature_key = feature.key if feature else None
    if "value" in form.fields:
        form.fields["value"].choices = value_choices(
            feature_key,
            include_guarded=include_guarded,
        )
    if "page" in form.fields:
        form.fields["page"].choices = page_choices(feature_key)
        choices = form.fields["page"].choices
        form.page_is_fixed = len(choices) <= 1
        if not form.is_bound and len(choices) == 1:
            form.initial.setdefault("page", choices[0][0])


def _attach_registry_options(
    form: forms.Form,
    *,
    request_user=None,
    include_guarded: bool = True,
) -> None:
    if "feature" not in form.fields:
        return
    options = {}
    audience_tokens = {
        FeatureRuleType.GROUP: RolloutAudience.GROUP,
        FeatureRuleType.USER_ALLOWLIST: RolloutAudience.USERS,
        FeatureRuleType.STAFF: RolloutAudience.STAFF,
        FeatureRuleType.AUTHENTICATED: RolloutAudience.AUTHENTICATED,
        FeatureRuleType.PERCENTAGE: RolloutAudience.PERCENTAGE,
        FeatureRuleType.EVERYONE: RolloutAudience.EVERYONE,
    }
    for feature in form.fields["feature"].queryset:
        spec = FEATURE_REGISTRY[feature.key]
        default_token = canonical_value(get_effective_default(feature))
        allowed_values = value_choices(
            feature.key,
            include_guarded=include_guarded,
        )
        suggested_value = next(
            (
                token
                for token, _label in allowed_values
                if token != default_token
            ),
            allowed_values[0][0] if allowed_values else "",
        )
        audiences = [
            audience_tokens[token]
            for token in get_allowed_audiences(feature.key)
            if token in audience_tokens
        ]
        if request_user is not None:
            if not request_user.has_perm("auth.view_user"):
                audiences = [
                    value
                    for value in audiences
                    if value != RolloutAudience.USERS
                ]
            if not request_user.has_perm(
                "featureflags.change_featuredefinition"
            ):
                audiences = [
                    value
                    for value in audiences
                    if value not in RolloutAudience.DANGEROUS
                ]
        required_group_slug = get_required_group_slug(feature.key)
        required_group_id = None
        if required_group_slug:
            required_group_id = (
                FeatureGroup.objects.filter(slug=required_group_slug)
                .values_list("pk", flat=True)
                .first()
            )
        options[str(feature.pk)] = {
            "title": get_feature_title(feature.key),
            "key": feature.key,
            "description": spec.get("description") or "",
            "visual_impact": spec.get("visual_impact") or "",
            "default": dict(value_choices(feature.key)).get(
                default_token,
                default_token,
            ),
            "default_token": default_token,
            "suggested_value": suggested_value,
            "sticky": bool(spec.get("sticky")),
            "values": allowed_values,
            "pages": page_choices(feature.key),
            "audiences": audiences,
            "rule_types": tuple(
                (str(token), str(label))
                for token, label in FeatureRuleType.choices
                if not is_design_flag(feature.key)
                or is_audience_allowed(feature.key, token)
            ),
            "required_group": required_group_slug,
            "required_group_id": required_group_id,
        }
    form.fields["feature"].widget.attrs["data-registry-options"] = json.dumps(
        options,
        ensure_ascii=False,
    )


class UserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj) -> str:
        return user_label(obj)


class UserMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj) -> str:
        return user_label(obj)


class FeatureDefinitionChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj) -> str:
        return f"{get_feature_title(obj.key)} — {obj.key}"


class FeatureRuleAdminForm(forms.ModelForm):
    feature = FeatureDefinitionChoiceField(
        label="Фича-флаг",
        queryset=FeatureDefinition.objects.none(),
    )
    audit_reason = forms.CharField(
        label="Причина изменения",
        min_length=5,
        max_length=100,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Обязательная причина попадёт в историю изменений.",
    )
    value = forms.ChoiceField(
        label="Значение",
        choices=(),
        help_text="Допустимые значения берутся из реестра в коде.",
    )
    page = forms.ChoiceField(
        label="Страница",
        choices=(),
        required=False,
        help_text="«Все страницы» сохраняется как глобальное правило.",
    )
    target_users = UserMultipleChoiceField(
        queryset=User.objects.order_by("username", "email"),
        required=False,
        label="Пользователи",
        widget=admin.widgets.FilteredSelectMultiple("Пользователи", False),
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
        widget=forms.SelectMultiple(attrs={"size": 6}),
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
        self.fields[
            "priority"
        ].help_text = "Меньшее число проверяется раньше. Обычно оставьте 100."
        self.fields["feature"].queryset = FeatureDefinition.objects.filter(
            active=True,
            key__in=FEATURE_REGISTRY,
        ).order_by("key")
        _attach_registry_options(self)
        _configure_registry_fields(self)
        selected_rule_type = (
            self.data.get(self.add_prefix("rule_type"))
            if self.is_bound
            else getattr(self.instance, "rule_type", None)
        )
        if selected_rule_type in {
            FeatureRuleType.USER_DENYLIST,
            FeatureRuleType.ANONYMOUS_DENYLIST,
        }:
            self.fields["value"].required = False
        if not self.instance.pk:
            return

        if self.instance.rule_type in {
            FeatureRuleType.USER_ALLOWLIST,
            FeatureRuleType.USER_DENYLIST,
        }:
            self.fields["target_users"].initial = User.objects.filter(
                pk__in=parse_int_values(self.instance.actor_ids or [])
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
                pk__in=parse_int_values(self.instance.group_ids or [])
            )

    def clean(self):
        cleaned_data = super().clean()
        feature = cleaned_data.get("feature")
        rule_type = cleaned_data.get("rule_type")
        page = cleaned_data.get("page", "")

        if feature and feature.key not in FEATURE_REGISTRY:
            self.add_error("feature", "Флаг не объявлен в реестре приложения.")

        if rule_type == FeatureRuleType.GROUP:
            if not cleaned_data.get("target_groups"):
                self.add_error(
                    "target_groups", "Выберите хотя бы одну группу."
                )
        elif rule_type in {
            FeatureRuleType.USER_ALLOWLIST,
            FeatureRuleType.USER_DENYLIST,
        }:
            if not cleaned_data.get("target_users"):
                self.add_error(
                    "target_users", "Выберите хотя бы одного пользователя."
                )
        elif rule_type in {
            FeatureRuleType.ANONYMOUS_ALLOWLIST,
            FeatureRuleType.ANONYMOUS_DENYLIST,
        }:
            if not split_text_values(cleaned_data.get("anonymous_ids")):
                self.add_error(
                    "anonymous_ids",
                    "Добавьте хотя бы один анонимный идентификатор.",
                )
        elif rule_type == FeatureRuleType.PERCENTAGE:
            percentage = cleaned_data.get("percentage")
            if percentage is None:
                self.add_error("percentage", "Укажите процент раската.")
            elif not 0 <= percentage <= 100:
                self.add_error(
                    "percentage", "Используйте значение от 0 до 100."
                )

        if feature and not self.errors.get("feature"):
            allowed_pages = {choice[0] for choice in page_choices(feature.key)}
            if page not in allowed_pages:
                self.add_error(
                    "page", "Страница не разрешена реестром этого флага."
                )
            self._validate_policy(feature, rule_type)
            self._validate_conflict(feature, rule_type, page)
            if rule_type in {
                FeatureRuleType.USER_DENYLIST,
                FeatureRuleType.ANONYMOUS_DENYLIST,
            }:
                cleaned_data["value"] = canonical_value(
                    get_effective_default(feature)
                )
        return cleaned_data

    def _validate_policy(self, feature, rule_type) -> None:
        if not rule_type:
            return
        # Deny/anonymous rules remain advanced operations for regular flags,
        # but a flag with an explicit registry policy must never be widened by
        # a crafted admin POST.
        if is_design_flag(feature.key) and not is_audience_allowed(
            feature.key, rule_type
        ):
            self.add_error(
                "rule_type",
                "Политика реестра не разрешает эту аудиторию для флага.",
            )
            return
        required_slug = get_required_group_slug(feature.key)
        if required_slug and rule_type == FeatureRuleType.GROUP:
            groups = list(self.cleaned_data.get("target_groups") or [])
            if not groups or any(
                group.slug != required_slug for group in groups
            ):
                self.add_error(
                    "target_groups",
                    f"Политика реестра требует группу {required_slug}.",
                )

    def _validate_conflict(self, feature, rule_type, page: str) -> None:
        if not self.cleaned_data.get("enabled") or not rule_type:
            return
        conflicts = FeatureRule.objects.filter(
            feature=feature,
            rule_type=rule_type,
            enabled=True,
        )
        if page:
            conflicts = conflicts.filter(Q(page="") | Q(page=page))
        if self.instance.pk:
            conflicts = conflicts.exclude(pk=self.instance.pk)
        if conflicts.exists():
            self.add_error(
                None,
                "Для этого флага и аудитории уже есть пересекающееся "
                "активное правило. "
                "Остановите его или отредактируйте существующее.",
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        rule_type = self.cleaned_data.get("rule_type")

        if rule_type in {
            FeatureRuleType.USER_DENYLIST,
            FeatureRuleType.ANONYMOUS_DENYLIST,
        }:
            instance.value = canonical_value(
                get_effective_default(instance.feature)
            )

        instance.percentage = (
            self.cleaned_data.get("percentage")
            if rule_type == FeatureRuleType.PERCENTAGE
            else None
        )
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
            instance.actor_ids = split_text_values(
                self.cleaned_data.get("anonymous_ids")
            )
            instance.group_ids = []
        else:
            instance.actor_ids = []
            instance.group_ids = []

        if commit:
            instance.full_clean()
            instance.save()
            self.save_m2m()
        return instance

    class Media:
        css = {"all": ("featureflags/admin_rollout.css",)}
        js = ("featureflags/admin_rollout.js",)


class FeatureOverrideAdminForm(forms.ModelForm):
    feature = FeatureDefinitionChoiceField(
        label="Фича-флаг",
        queryset=FeatureDefinition.objects.none(),
    )
    value = forms.ChoiceField(
        label="Значение",
        choices=(),
        help_text="Допустимые значения берутся из реестра в коде.",
    )
    target_user = UserChoiceField(
        queryset=User.objects.order_by("username", "email"),
        required=False,
        label="Пользователь",
    )
    anonymous_scope = forms.CharField(
        required=False,
        label="Анонимный идентификатор",
    )
    confirm_global = forms.BooleanField(
        label="Я понимаю, что override затронет всех пользователей",
        required=False,
    )

    class Meta:
        model = FeatureOverride
        fields = ("feature", "scope_type", "value", "enabled", "note")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["note"].required = True
        self.fields[
            "note"
        ].help_text = (
            "Обязательная причина экстренного исключения попадёт в историю."
        )
        self.fields["feature"].queryset = FeatureDefinition.objects.filter(
            active=True,
            key__in=FEATURE_REGISTRY,
        ).order_by("key")
        _attach_registry_options(self, include_guarded=False)
        _configure_registry_fields(self, include_guarded=False)
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
        feature = cleaned_data.get("feature")
        scope_type = cleaned_data.get("scope_type")

        if feature and feature.key not in FEATURE_REGISTRY:
            self.add_error("feature", "Флаг не объявлен в реестре приложения.")
        if feature and cleaned_data.get("value") not in {
            token
            for token, _label in value_choices(
                feature.key,
                include_guarded=False,
            )
        }:
            self.add_error(
                "value",
                "Это значение запрещено политикой безопасных override.",
            )
        if scope_type == FeatureOverrideScope.USER:
            if not cleaned_data.get("target_user"):
                self.add_error("target_user", "Выберите пользователя.")
        elif scope_type == FeatureOverrideScope.ANONYMOUS:
            if not str(cleaned_data.get("anonymous_scope") or "").strip():
                self.add_error(
                    "anonymous_scope", "Укажите анонимный идентификатор."
                )
        elif (
            scope_type == FeatureOverrideScope.GLOBAL
            and not cleaned_data.get("confirm_global")
        ):
            self.add_error(
                "confirm_global",
                "Подтвердите глобальное экстренное исключение.",
            )
        if feature and scope_type:
            if scope_type == FeatureOverrideScope.USER:
                target = cleaned_data.get("target_user")
                scope_value = str(target.pk) if target else ""
            elif scope_type == FeatureOverrideScope.ANONYMOUS:
                scope_value = str(
                    cleaned_data.get("anonymous_scope") or ""
                ).strip()
            else:
                scope_value = ""
            duplicates = FeatureOverride.objects.filter(
                feature=feature,
                scope_type=scope_type,
                scope_value=scope_value,
            )
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise ValidationError(
                    "Для этого флага и области уже существует override. "
                    "Отредактируйте существующий."
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
            instance.full_clean()
            instance.save()
            self.save_m2m()
        return instance

    class Media:
        css = {"all": ("featureflags/admin_rollout.css",)}
        js = ("featureflags/admin_rollout.js",)


class GuidedRolloutForm(forms.Form):
    feature = FeatureDefinitionChoiceField(
        label="Фича-флаг",
        queryset=FeatureDefinition.objects.none(),
        help_text=(
            "Новые ключи сначала добавляются разработчиком в реестр кода."
        ),
    )
    value = forms.ChoiceField(label="Состояние", choices=())
    page = forms.ChoiceField(label="Страница", choices=(), required=False)
    audience = forms.ChoiceField(
        label="Кому показать", choices=RolloutAudience.CHOICES
    )
    target_groups = forms.ModelMultipleChoiceField(
        label="Группы",
        queryset=FeatureGroup.objects.order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 8}),
    )
    target_users = UserMultipleChoiceField(
        label="Пользователи",
        queryset=User.objects.filter(is_active=True).order_by(
            "username", "email"
        ),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 8}),
    )
    percentage = forms.IntegerField(
        label="Процент",
        min_value=0,
        max_value=100,
        required=False,
        help_text="Стабильное распределение от 0 до 100%.",
    )
    name = forms.CharField(
        label="Название",
        max_length=120,
        required=False,
        help_text=(
            "Можно оставить пустым — название будет сформировано "
            "автоматически."
        ),
    )
    reason = forms.CharField(
        label="Зачем нужен раскат",
        min_length=5,
        max_length=100,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Причина попадёт в неизменяемую историю изменений.",
    )
    enabled = forms.BooleanField(
        label="Запустить сразу",
        required=False,
        initial=True,
        help_text="Снимите флажок, чтобы сохранить безопасный черновик.",
    )
    confirm_dangerous = forms.BooleanField(
        label="Я понимаю, что это широкая аудитория",
        required=False,
    )
    confirm_rollout = forms.BooleanField(
        label="Я проверил флаг, значение, страницу и аудиторию",
        required=False,
    )

    def __init__(
        self,
        *args,
        request_user=None,
        require_confirmation: bool = False,
        **kwargs,
    ):
        self.request_user = request_user
        self.require_confirmation = require_confirmation
        super().__init__(*args, **kwargs)
        self.fields["feature"].queryset = FeatureDefinition.objects.filter(
            active=True,
            key__in=FEATURE_REGISTRY,
        ).order_by("key")
        self.registry_empty = not self.fields["feature"].queryset.exists()
        if not self.is_bound and not self.initial.get("feature"):
            self.initial["feature"] = self.fields["feature"].queryset.first()
        if request_user is not None and not request_user.has_perm(
            "auth.view_user"
        ):
            self.fields["target_users"].queryset = User.objects.none()
            self.fields["audience"].choices = tuple(
                choice
                for choice in RolloutAudience.CHOICES
                if choice[0] != RolloutAudience.USERS
            )
        if request_user is not None and not request_user.has_perm(
            "featureflags.change_featuredefinition"
        ):
            self.fields["audience"].choices = tuple(
                choice
                for choice in self.fields["audience"].choices
                if choice[0] not in RolloutAudience.DANGEROUS
            )
        _attach_registry_options(self, request_user=request_user)
        _configure_registry_fields(self)
        if not self.is_bound:
            requested_feature = self.initial.get("feature")
            feature = (
                requested_feature
                if isinstance(requested_feature, FeatureDefinition)
                else _selected_feature(self)
            )
            if feature:
                choices = value_choices(feature.key)
                default = canonical_value(get_effective_default(feature))
                non_default = [
                    value for value, _label in choices if value != default
                ]
                if non_default:
                    self.initial.setdefault("value", non_default[0])
                allowed_rules = get_allowed_audiences(feature.key)
                allowed_ui = [
                    audience
                    for audience, rule_type in AUDIENCE_TO_RULE_TYPE.items()
                    if rule_type in allowed_rules
                    and audience
                    in {
                        choice[0] for choice in self.fields["audience"].choices
                    }
                ]
                if allowed_ui:
                    self.initial.setdefault("audience", allowed_ui[0])
                required_slug = get_required_group_slug(feature.key)
                if required_slug:
                    group = FeatureGroup.objects.filter(
                        slug=required_slug
                    ).first()
                    if group:
                        self.initial.setdefault("target_groups", [group.pk])

    def clean(self):
        cleaned_data = super().clean()
        feature = cleaned_data.get("feature")
        audience = cleaned_data.get("audience")
        page = cleaned_data.get("page", "")

        if feature and feature.key not in FEATURE_REGISTRY:
            self.add_error("feature", "Флаг не объявлен в реестре приложения.")
            return cleaned_data

        if audience == RolloutAudience.GROUP:
            groups = list(cleaned_data.get("target_groups") or [])
            if not groups:
                self.add_error(
                    "target_groups", "Выберите хотя бы одну группу."
                )
        elif audience == RolloutAudience.USERS:
            if (
                self.request_user is not None
                and not self.request_user.has_perm("auth.view_user")
            ):
                self.add_error(
                    "audience",
                    "Нет права просматривать пользователей для этой "
                    "аудитории.",
                )
            if not cleaned_data.get("target_users"):
                self.add_error(
                    "target_users", "Выберите хотя бы одного пользователя."
                )
        elif audience == RolloutAudience.PERCENTAGE:
            if cleaned_data.get("percentage") is None:
                self.add_error("percentage", "Укажите процент раската.")

        if audience in RolloutAudience.DANGEROUS:
            if (
                self.request_user is not None
                and not self.request_user.has_perm(
                    "featureflags.change_featuredefinition"
                )
            ):
                self.add_error(
                    "audience",
                    "Широкий раскат требует повышенного права на определения.",
                )
            if not cleaned_data.get("confirm_dangerous"):
                self.add_error(
                    "confirm_dangerous", "Подтвердите широкий раскат."
                )

        if feature:
            allowed_pages = {choice[0] for choice in page_choices(feature.key)}
            if page not in allowed_pages:
                self.add_error(
                    "page", "Страница не разрешена реестром этого флага."
                )
            rule_type = AUDIENCE_TO_RULE_TYPE.get(audience)
            if rule_type and not is_audience_allowed(feature.key, rule_type):
                self.add_error(
                    "audience",
                    "Политика реестра не разрешает эту аудиторию для флага.",
                )
            required_slug = get_required_group_slug(feature.key)
            if required_slug and audience == RolloutAudience.GROUP:
                groups = list(cleaned_data.get("target_groups") or [])
                if not groups or any(
                    group.slug != required_slug for group in groups
                ):
                    raise ValidationError(
                        f"Политика реестра требует группу {required_slug}."
                    )

            if cleaned_data.get("enabled"):
                conflicts = FeatureRule.objects.filter(
                    feature=feature,
                    enabled=True,
                )
                if page:
                    conflicts = conflicts.filter(Q(page="") | Q(page=page))
                conflict = conflicts.order_by("priority", "id").first()
                if conflict:
                    raise ValidationError(
                        "Для этого флага уже есть пересекающийся "
                        "активный раскат "
                        f"«{conflict.name}». Сначала остановите его."
                    )
        if self.require_confirmation and not cleaned_data.get(
            "confirm_rollout"
        ):
            self.add_error(
                "confirm_rollout", "Подтвердите итоговые параметры раската."
            )
        return cleaned_data

    class Media:
        css = {"all": ("featureflags/admin_rollout.css",)}
        js = ("featureflags/admin_rollout.js",)


class StopRolloutForm(forms.Form):
    reason = forms.CharField(
        label="Причина остановки",
        min_length=5,
        max_length=100,
        widget=forms.Textarea(attrs={"rows": 2}),
    )


class DesignTesterForm(forms.Form):
    user = UserChoiceField(
        label="Пользователь",
        queryset=User.objects.filter(is_active=True).order_by(
            "username", "email"
        ),
    )
    reason = forms.CharField(
        label="Причина добавления",
        min_length=5,
        max_length=100,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
