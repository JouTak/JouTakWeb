from __future__ import annotations

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from featureflags.forms import (
    RolloutAudience,
    canonical_value,
    page_choices,
    value_choices,
)
from featureflags.models import (
    FeatureDefinition,
    FeatureGroup,
    FeatureRule,
    FeatureRuleType,
)
from featureflags.registry import (
    DESIGN_TESTER_GROUP_SLUG,
    FEATURE_REGISTRY,
    get_required_group_slug,
    is_audience_allowed,
)

AUDIENCE_RULE_TYPES = {
    RolloutAudience.GROUP: FeatureRuleType.GROUP,
    RolloutAudience.USERS: FeatureRuleType.USER_ALLOWLIST,
    RolloutAudience.STAFF: FeatureRuleType.STAFF,
    RolloutAudience.AUTHENTICATED: FeatureRuleType.AUTHENTICATED,
    RolloutAudience.PERCENTAGE: FeatureRuleType.PERCENTAGE,
    RolloutAudience.EVERYONE: FeatureRuleType.EVERYONE,
}


def _audit(instance, *, user, reason: str) -> None:
    instance._history_user = user
    instance._change_reason = reason.strip()[:100]


def _is_original_draft(rule: FeatureRule) -> bool:
    """Distinguish a saved draft from a rollout that was later stopped."""
    created = rule.history.order_by("history_date", "history_id").first()
    return bool(created and not created.enabled)


def _validated_group_ids(raw_group_ids: object) -> list[int]:
    """Parse stored JSON group IDs without silently dropping corruption."""
    if not isinstance(raw_group_ids, list):
        raise ValidationError("Список групп раската повреждён.")
    parsed: set[int] = set()
    for raw_group_id in raw_group_ids:
        if isinstance(raw_group_id, bool):
            raise ValidationError("Список групп раската повреждён.")
        if isinstance(raw_group_id, int):
            group_id = raw_group_id
        elif isinstance(raw_group_id, str) and raw_group_id.strip().isdigit():
            group_id = int(raw_group_id.strip())
        else:
            raise ValidationError("Список групп раската повреждён.")
        if group_id <= 0:
            raise ValidationError("Список групп раската повреждён.")
        parsed.add(group_id)
    return sorted(parsed)


def _active_conflict(
    *,
    feature: FeatureDefinition,
    page: str,
    exclude_rule_id: int | None = None,
) -> FeatureRule | None:
    """Find a rule whose page scope overlaps the requested rollout."""
    conflicts = FeatureRule.objects.filter(feature=feature, enabled=True)
    if page:
        conflicts = conflicts.filter(Q(page="") | Q(page=page))
    if exclude_rule_id is not None:
        conflicts = conflicts.exclude(pk=exclude_rule_id)
    return conflicts.order_by("priority", "id").first()


@transaction.atomic
def create_rollout(*, cleaned_data: dict, user) -> FeatureRule:
    """Create one rollout from the safe admin form under a feature lock."""
    requested_feature = cleaned_data["feature"]
    feature = FeatureDefinition.objects.select_for_update().get(
        pk=requested_feature.pk
    )
    if not feature.active or feature.key not in FEATURE_REGISTRY:
        raise ValidationError("Флаг больше не доступен для раската.")

    page = cleaned_data.get("page") or ""
    audience = cleaned_data["audience"]
    try:
        rule_type = AUDIENCE_RULE_TYPES[audience]
    except KeyError as exc:
        raise ValidationError("Неизвестная аудитория раската.") from exc
    if not is_audience_allowed(feature.key, rule_type):
        raise ValidationError(
            "Политика реестра не разрешает эту аудиторию для флага."
        )
    if audience in RolloutAudience.DANGEROUS and not user.has_perm(
        "featureflags.change_featuredefinition"
    ):
        raise ValidationError(
            "Широкий раскат требует повышенного права на определения."
        )
    if audience == RolloutAudience.USERS and not user.has_perm(
        "auth.view_user"
    ):
        raise ValidationError(
            "Нет права просматривать пользователей для этой аудитории."
        )
    if audience == RolloutAudience.GROUP and not user.has_perm(
        "featureflags.view_featuregroup"
    ):
        raise ValidationError(
            "Нет права просматривать группы для этой аудитории."
        )

    value = canonical_value(cleaned_data.get("value"))
    allowed_values = {token for token, _label in value_choices(feature.key)}
    if value not in allowed_values:
        raise ValidationError("Значение не разрешено реестром этого флага.")
    allowed_pages = {token for token, _label in page_choices(feature.key)}
    if page not in allowed_pages:
        raise ValidationError("Страница не разрешена реестром этого флага.")

    groups = list(cleaned_data.get("target_groups") or [])
    users = list(cleaned_data.get("target_users") or [])
    required_slug = get_required_group_slug(feature.key)
    if required_slug:
        if (
            rule_type != FeatureRuleType.GROUP
            or not groups
            or any(group.slug != required_slug for group in groups)
        ):
            raise ValidationError(
                f"Политика реестра требует группу {required_slug}."
            )
    if rule_type == FeatureRuleType.GROUP and not groups:
        raise ValidationError("Выберите хотя бы одну группу.")
    if rule_type == FeatureRuleType.USER_ALLOWLIST and not users:
        raise ValidationError("Выберите хотя бы одного пользователя.")
    percentage = cleaned_data.get("percentage")
    if rule_type == FeatureRuleType.PERCENTAGE and (
        percentage is None or not 0 <= percentage <= 100
    ):
        raise ValidationError("Используйте процент от 0 до 100.")

    enabled = bool(cleaned_data.get("enabled"))
    if enabled:
        conflict = _active_conflict(feature=feature, page=page)
        if conflict:
            raise ValidationError(
                "Для этого флага и страницы уже есть активный раскат "
                f"«{conflict.name}»."
            )

    reason = str(cleaned_data.get("reason") or "").strip()
    if len(reason) < 5:
        raise ValidationError("Укажите причину длиной не менее 5 символов.")

    audience_label = dict(RolloutAudience.CHOICES)[audience]
    actor_ids = (
        sorted(str(target.pk) for target in users)
        if rule_type == FeatureRuleType.USER_ALLOWLIST
        else []
    )
    group_ids = (
        sorted(group.pk for group in groups)
        if rule_type == FeatureRuleType.GROUP
        else []
    )
    name = (cleaned_data.get("name") or f"{feature.key}: {audience_label}")[
        :120
    ]
    stored_percentage = (
        percentage if rule_type == FeatureRuleType.PERCENTAGE else None
    )

    # A signed confirmation can be retried by a browser or reverse proxy.
    # The feature row lock makes looking up an identical original draft and
    # creating it a single serialized operation. A rollout that was once
    # active and later stopped is intentionally not treated as a draft.
    if not enabled:
        matching_drafts = FeatureRule.objects.select_for_update().filter(
            feature=feature,
            name=name,
            priority=100,
            rule_type=rule_type,
            value=value,
            page=page,
            actor_ids=actor_ids,
            group_ids=group_ids,
            percentage=stored_percentage,
            enabled=False,
        )
        for existing in matching_drafts:
            if _is_original_draft(existing):
                existing._rollout_was_created = False
                return existing

    rule = FeatureRule(
        feature=feature,
        name=name,
        priority=100,
        rule_type=rule_type,
        value=value,
        page=page,
        actor_ids=actor_ids,
        group_ids=group_ids,
        percentage=stored_percentage,
        enabled=enabled,
    )
    _audit(rule, user=user, reason=reason)
    rule.full_clean()
    rule.save()
    rule._rollout_was_created = True
    return rule


@transaction.atomic
def stop_rollout(*, rule_id: int, user, reason: str) -> FeatureRule:
    rule = (
        FeatureRule.objects.select_for_update()
        .select_related("feature")
        .get(pk=rule_id)
    )
    if not rule.feature.active or rule.feature.key not in FEATURE_REGISTRY:
        raise ValidationError(
            "Архивный или неизвестный флаг нельзя менять через раскаты."
        )
    if not rule.enabled:
        raise ValidationError("Раскат уже остановлен.")
    if len(reason.strip()) < 5:
        raise ValidationError("Укажите причину длиной не менее 5 символов.")
    rule.enabled = False
    _audit(rule, user=user, reason=reason)
    rule.full_clean()
    rule.save(update_fields=("enabled", "updated_at"))
    return rule


@transaction.atomic
def start_rollout(*, rule_id: int, user, reason: str) -> FeatureRule:
    candidate = FeatureRule.objects.only("feature_id").get(pk=rule_id)
    feature = FeatureDefinition.objects.select_for_update().get(
        pk=candidate.feature_id
    )
    rule = FeatureRule.objects.select_for_update().get(pk=rule_id)
    if rule.enabled:
        raise ValidationError("Раскат уже запущен.")
    if not feature.active or feature.key not in FEATURE_REGISTRY:
        raise ValidationError("Флаг больше не доступен для раската.")
    if not _is_original_draft(rule):
        raise ValidationError(
            "Запустить можно только раскат, созданный как черновик."
        )
    if not is_audience_allowed(feature.key, rule.rule_type):
        raise ValidationError(
            "Политика реестра больше не разрешает аудиторию."
        )
    if rule.rule_type in {
        FeatureRuleType.AUTHENTICATED,
        FeatureRuleType.PERCENTAGE,
        FeatureRuleType.EVERYONE,
    } and not user.has_perm("featureflags.change_featuredefinition"):
        raise ValidationError(
            "Широкий раскат требует повышенного права на определения."
        )
    if rule.rule_type in {
        FeatureRuleType.USER_ALLOWLIST,
        FeatureRuleType.USER_DENYLIST,
    } and not user.has_perm("auth.view_user"):
        raise ValidationError(
            "Нет права просматривать пользователей этого раската."
        )
    if rule.rule_type == FeatureRuleType.GROUP and not user.has_perm(
        "featureflags.view_featuregroup"
    ):
        raise ValidationError("Нет права просматривать группы этого раската.")
    if (
        rule.rule_type
        in {
            FeatureRuleType.USER_ALLOWLIST,
            FeatureRuleType.USER_DENYLIST,
        }
        and not rule.actor_ids
    ):
        raise ValidationError("В раскате не выбраны пользователи.")
    selected_group_slugs: set[str] | None = None
    if rule.rule_type == FeatureRuleType.GROUP:
        group_ids = _validated_group_ids(rule.group_ids)
        selected_groups = list(
            FeatureGroup.objects.select_for_update().filter(pk__in=group_ids)
        )
        if not group_ids or len(selected_groups) != len(group_ids):
            raise ValidationError("В раскате не выбраны существующие группы.")
        selected_group_slugs = {group.slug for group in selected_groups}
    if rule.rule_type == FeatureRuleType.PERCENTAGE:
        percentage = rule.percentage
        if (
            isinstance(percentage, bool)
            or not isinstance(percentage, int)
            or not 0 <= percentage <= 100
        ):
            raise ValidationError("Используйте процент от 0 до 100.")
    if rule.value not in {
        token for token, _label in value_choices(feature.key)
    }:
        raise ValidationError("Значение больше не разрешено реестром.")
    if rule.page not in {token for token, _label in page_choices(feature.key)}:
        raise ValidationError("Страница больше не разрешена реестром.")
    required_slug = get_required_group_slug(feature.key)
    if required_slug:
        if selected_group_slugs != {required_slug}:
            raise ValidationError(
                f"Политика реестра требует группу {required_slug}."
            )
    conflict = _active_conflict(
        feature=feature,
        page=rule.page,
        exclude_rule_id=rule.pk,
    )
    if conflict:
        raise ValidationError(
            "Для этого флага и страницы уже есть активный раскат "
            f"«{conflict.name}»."
        )
    if len(reason.strip()) < 5:
        raise ValidationError("Укажите причину длиной не менее 5 символов.")
    rule.enabled = True
    rule.feature = feature
    _audit(rule, user=user, reason=reason)
    rule.full_clean()
    rule.save(update_fields=("enabled", "updated_at"))
    return rule


@transaction.atomic
def add_design_tester(*, target_user, user, reason: str) -> FeatureGroup:
    if not user.has_perms(
        ("featureflags.change_featuregroup", "auth.view_user")
    ):
        raise ValidationError(
            "Недостаточно прав для управления дизайн-тестерами."
        )
    if not target_user.is_active:
        raise ValidationError("Нельзя добавить неактивного пользователя.")
    if len(reason.strip()) < 5:
        raise ValidationError("Укажите причину длиной не менее 5 символов.")
    group = FeatureGroup.objects.select_for_update().get(
        slug=DESIGN_TESTER_GROUP_SLUG
    )
    already_member = group.members.filter(pk=target_user.pk).exists()
    if not already_member:
        group.members.add(target_user)
    LogEntry.objects.create(
        user_id=user.pk,
        content_type=ContentType.objects.get_for_model(FeatureGroup),
        object_id=str(group.pk),
        object_repr=str(group)[:200],
        action_flag=CHANGE,
        change_message=(
            f"{'Confirmed' if already_member else 'Added'} design tester "
            f"{target_user.get_username()}: {reason.strip()[:100]}"
        ),
    )
    return group
