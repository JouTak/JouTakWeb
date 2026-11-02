from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from playergroups.common import locked_group, record
from playergroups.models import (
    GroupInvitation,
    GroupJoinRequest,
    GroupMembership,
)
from playergroups.policies import GroupPolicy, fail, guard_last_manager
from playergroups.process_state import (
    clean_pending,
    close_all,
    close_process,
    process_status,
)


def activate(group, user, actor, visibility):
    member, created = GroupMembership.objects.get_or_create(
        group=group, user=user, defaults={"visibility": visibility}
    )
    joined = created or member.status != "active"
    if not created and joined:
        member.status, member.role, member.visibility = (
            "active",
            "member",
            visibility,
        )
        member.joined_at, member.left_at = timezone.now(), None
        member.save()
    for model in (GroupJoinRequest, GroupInvitation):
        for process in model.objects.filter(
            group=group, user=user, status="pending"
        ):
            process.group = group
            close_process(process, actor, "accepted", "Участие подтверждено.")
    if joined:
        record(group, actor, "member_joined", target=user)
    return member


def join(actor, slug, payload):
    with locked_group(slug, [actor.pk]) as group:
        policy = GroupPolicy(actor, group)
        policy.require("view")
        if policy.role:
            return group
        policy.require_entry()
        if group.join_mode != "open":
            fail(
                "JOIN_MODE",
                "Для этого объединения нужен другой способ вступления.",
            )
        clean_pending(group)
        activate(group, actor, actor, payload.visibility)
        return group


def apply(actor, slug, payload):
    with locked_group(slug, [actor.pk]) as group:
        policy = GroupPolicy(actor, group)
        policy.require("view")
        policy.require_entry()
        if policy.role:
            fail("ALREADY_MEMBER", "Вы уже участвуете в объединении.")
        if group.join_mode != "approval":
            fail(
                "JOIN_MODE", "Сейчас заявки в это объединение не принимаются."
            )
        clean_pending(group)
        existing = GroupJoinRequest.objects.filter(
            group=group, user=actor, status="pending"
        ).first()
        if existing:
            return existing
        if group.application_question and not payload.answer:
            fail("ANSWER_REQUIRED", "Ответьте на вопрос организаторов.", 422)
        if (
            GroupJoinRequest.objects.filter(
                user=actor, created_at__gte=timezone.now() - timedelta(days=1)
            ).count()
            >= settings.GROUPS_REQUESTS_PER_DAY
        ):
            fail(
                "REQUEST_LIMIT",
                "Лимит заявок за сутки исчерпан. Попробуйте позже.",
                429,
            )
        if GroupJoinRequest.objects.filter(
            group=group,
            user=actor,
            status="rejected",
            resolved_at__gt=timezone.now() - timedelta(days=1),
        ).exists():
            fail(
                "REQUEST_COOLDOWN",
                "Повторную заявку можно подать через сутки после решения.",
            )
        process = GroupJoinRequest.objects.create(
            group=group,
            user=actor,
            answer=payload.answer,
            visibility=payload.visibility,
            expires_at=timezone.now()
            + timedelta(days=settings.GROUPS_REQUEST_DAYS),
        )
        record(group, actor, "request_sent", target=actor)
        return process


def decide_request(actor, slug, request_id, payload=None, *, withdraw=False):
    lookup = GroupJoinRequest.objects.filter(group__slug=slug, pk=request_id)
    if withdraw:
        lookup = lookup.filter(user=actor)
    target_id = lookup.values_list("user_id", flat=True).first()
    with locked_group(slug, [actor.pk, target_id]) as group:
        if not withdraw:
            GroupPolicy(actor, group).require("manage")
        process = (
            group.groupjoinrequest_set.filter(
                pk=request_id, **({"user": actor} if withdraw else {})
            )
            .select_related("user")
            .first()
        )
        if not process:
            fail("REQUEST_NOT_FOUND", "Заявка недоступна.", 404)
        process.group = group
        desired = (
            "cancelled"
            if withdraw
            else "accepted"
            if payload.decision == "accept"
            else "rejected"
        )
        if process.status == desired:
            return process
        if process_status(process) != "pending":
            fail("PROCESS_CLOSED", "Заявка уже завершена или истекла.")
        if desired == "accepted":
            GroupPolicy(process.user, group).require_entry()
            activate(group, process.user, actor, process.visibility)
            process.refresh_from_db()
        else:
            close_process(
                process,
                actor,
                desired,
                "Отозвано заявителем." if withdraw else payload.reason,
            )
        return process


def leave(actor, slug):
    with locked_group(slug, [actor.pk]) as group:
        member = group.memberships.filter(user=actor).first()
        if not member:
            fail("MEMBERSHIP_NOT_FOUND", "Участие недоступно.", 404)
        if member.status != "active":
            return
        guard_last_manager(group, member)
        member.status, member.role, member.left_at = (
            "left",
            "member",
            timezone.now(),
        )
        member.save()
        close_all(group, actor, "Участие завершено.", user=actor)
        clean_pending(group)
        record(group, actor, "member_left", target=actor)


def set_visibility(actor, slug, visibility):
    with locked_group(slug, [actor.pk]) as group:
        member = group.memberships.filter(user=actor, status="active").first()
        if not member:
            fail("MEMBERSHIP_NOT_FOUND", "Участие недоступно.", 404)
        if member.visibility != visibility:
            member.visibility = visibility
            member.save(update_fields=["visibility", "updated_at"])
            record(group, actor, "member_visibility_changed", target=actor)
