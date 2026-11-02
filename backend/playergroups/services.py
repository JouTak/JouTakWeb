from datetime import timedelta

from communities.access import authenticated
from communities.models import Community
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from playergroups.common import locked_group, record
from playergroups.models import GroupContact, GroupMembership, PlayerGroup
from playergroups.policies import (
    GroupPolicy,
    effective_members,
    eligible,
    fail,
)
from playergroups.process_state import close_all
from playergroups.schemas import AuditMetadata

SETTINGS_FIELDS = {
    "name",
    "short_description",
    "category",
    "rules",
    "application_question",
    "access",
    "join_mode",
    "accepting",
    "roster_visibility",
}


def check_version(group, version):
    if version != group.version:
        fail(
            "VERSION_CONFLICT",
            "Данные изменились. Обновите страницу перед сохранением.",
        )


@transaction.atomic
def create_group(actor, payload):
    if not authenticated(actor):
        fail("AUTH_REQUIRED", "Войдите в аккаунт.", 401)
    if (
        not get_user_model()
        .objects.select_for_update(no_key=True)
        .filter(pk=actor.pk, is_active=True)
        .first()
    ):
        fail("AUTH_REQUIRED", "Аккаунт недоступен.", 401)
    scope = None
    if payload.scope_slug:
        scope = Community.objects.filter(
            slug=payload.scope_slug,
            status="active",
            memberships__user=actor,
            memberships__status="active",
        ).first()
        if not scope:
            fail(
                "SCOPE_REQUIRED",
                "Выберите сообщество, в котором вы участвуете.",
                403,
            )
    existing = PlayerGroup.objects.filter(slug=payload.slug).first()
    if existing:
        if (
            existing.created_by_id == actor.pk
            and all(
                getattr(existing, key) == getattr(payload, key)
                for key in ("name", "short_description", "category")
            )
            and existing.scope_id == getattr(scope, "pk", None)
        ):
            return existing
        fail("SLUG_CONFLICT", "Этот адрес уже занят. Выберите другой.")
    if (
        PlayerGroup.objects.filter(
            created_by=actor,
            created_at__gte=timezone.now() - timedelta(days=1),
        ).count()
        >= settings.GROUPS_CREATE_PER_DAY
    ):
        fail(
            "CREATE_LIMIT",
            "Лимит новых объединений за сутки исчерпан. Попробуйте завтра.",
            429,
        )
    try:
        with transaction.atomic():
            group = PlayerGroup.objects.create(
                **payload.model_dump(exclude={"scope_slug"}),
                scope=scope,
                created_by=actor,
            )
    except IntegrityError:
        fail("SLUG_CONFLICT", "Этот адрес уже занят. Выберите другой.")
    GroupMembership.objects.create(group=group, user=actor, role="manager")
    record(group, actor, "group_created")
    return group


def update_group(actor, slug, payload):
    with locked_group(slug, [actor.pk]) as group:
        policy = GroupPolicy(actor, group)
        policy.require("manage")
        if group.status == "archived":
            fail("ARCHIVED", "Сначала восстановите объединение из архива.")
        check_version(group, payload.version)
        values = payload.model_dump(exclude_unset=True, exclude={"version"})
        if any(value is None for value in values.values()):
            fail("INVALID_FIELD", "Поля нельзя заменять на null.", 422)
        if set(values) & SETTINGS_FIELDS:
            policy.require("configure")
        contacts = values.pop("contacts", None)
        before = {key: getattr(group, key) for key in values}
        for key, value in values.items():
            setattr(group, key, value)
        if group.access == "private" and group.join_mode != "invite_only":
            fail(
                "PRIVATE_INVITATION_ONLY",
                "Для закрытого объединения выберите "
                "вступление по приглашению.",
                422,
            )
        changed = [key for key in values if before[key] != values[key]]
        if contacts is not None:
            previous = list(
                group.contacts.values("type", "label", "url", "visibility")
            )
            if previous != contacts:
                group.contacts.all().delete()
                GroupContact.objects.bulk_create(
                    [
                        GroupContact(group=group, sort_order=i, **c)
                        for i, c in enumerate(contacts)
                    ]
                )
                changed.append("contacts")
        if changed:
            group.version += 1
            group.save()
            record(
                group,
                actor,
                "group_updated",
                metadata=AuditMetadata(changed_fields=changed),
            )
        return group


def lifecycle(actor, slug, payload):
    with locked_group(slug, [actor.pk]) as group:
        policy = GroupPolicy(actor, group)
        # Archived managers retain only the narrowly scoped restore action.
        if (
            payload.action == "restore"
            and policy.role == "manager"
            and not group.restricted
        ):
            pass
        else:
            policy.require("configure")
        check_version(group, payload.version)
        expected = {
            "publish": "draft",
            "archive": "active",
            "restore": "archived",
        }[payload.action]
        if group.status != expected:
            fail("STATE_CONFLICT", "Состояние объединения уже изменилось.")
        if group.restricted:
            fail(
                "RESTRICTED", "Сначала требуется снять ограничение платформы."
            )
        if (
            payload.action != "archive"
            and not effective_members(group).filter(role="manager").exists()
        ):
            fail(
                "LAST_MANAGER",
                "Для публикации нужен действующий руководитель.",
            )
        group.status = "archived" if payload.action == "archive" else "active"
        if payload.action == "archive":
            group.archived_at = timezone.now()
            group.accepting = False
            close_all(group, actor, "Объединение архивировано.")
        elif payload.action == "restore":
            group.archived_at = None
            group.accepting = False
        else:
            group.published_at = timezone.now()
        group.version += 1
        group.save()
        record(group, actor, f"group_{payload.action}")
        return group


def require_join_target(user, group):
    if not eligible(user, group):
        fail(
            "PLAYER_UNAVAILABLE",
            "Игрок недоступен для участия в этом объединении.",
            422,
        )
    GroupPolicy(user, group).require_entry()
