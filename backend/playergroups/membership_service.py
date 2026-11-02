from django.utils import timezone

from playergroups.common import locked_group, record
from playergroups.models import GroupMembership, GroupRestriction
from playergroups.policies import GroupPolicy, fail, guard_last_manager
from playergroups.process_state import clean_pending, close_all
from playergroups.schemas import AuditMetadata


def target_member(group, member_id):
    member = (
        group.memberships.select_related("user").filter(pk=member_id).first()
    )
    if not member:
        fail("MEMBERSHIP_NOT_FOUND", "Участник недоступен.", 404)
    return member


def target_id(slug, member_id):
    return (
        GroupMembership.objects.filter(group__slug=slug, pk=member_id)
        .values_list("user_id", flat=True)
        .first()
    )


def change_role(actor, slug, member_id, payload):
    with locked_group(slug, [actor.pk, target_id(slug, member_id)]) as group:
        policy = GroupPolicy(actor, group)
        policy.require("configure")
        member = target_member(group, member_id)
        policy.require_target(member, role_change=True)
        if member.status != "active":
            fail("MEMBERSHIP_INACTIVE", "Участие уже завершено.")
        if member.role == payload.role:
            return
        if member.role == "manager":
            if not payload.reason:
                fail(
                    "REASON_REQUIRED",
                    "Укажите основание снятия руководителя.",
                    422,
                )
            guard_last_manager(group, member)
        before = member.role
        member.role = payload.role
        member.save(update_fields=["role", "updated_at"])
        clean_pending(group)
        record(
            group,
            actor,
            "role_changed",
            target=member.user,
            metadata=AuditMetadata(
                before_role=before,
                after_role=member.role,
                reason=payload.reason or None,
            ),
        )


def remove_member(actor, slug, member_id, reason):
    with locked_group(slug, [actor.pk, target_id(slug, member_id)]) as group:
        GroupPolicy(actor, group).require("manage")
        member = target_member(group, member_id)
        GroupPolicy(actor, group).require_target(member)
        if member.status == "removed":
            return
        if member.role == "manager" and not reason:
            fail(
                "REASON_REQUIRED",
                "Укажите основание снятия руководителя.",
                422,
            )
        guard_last_manager(group, member)
        member.status, member.role, member.left_at = (
            "removed",
            "member",
            timezone.now(),
        )
        member.save()
        close_all(group, actor, "Участие прекращено.", user=member.user)
        clean_pending(group)
        record(
            group,
            actor,
            "member_removed",
            target=member.user,
            metadata=AuditMetadata(reason=reason or None),
        )


def restrict_member(actor, slug, member_id, payload):
    with locked_group(slug, [actor.pk, target_id(slug, member_id)]) as group:
        policy = GroupPolicy(actor, group)
        policy.require("manage")
        member = target_member(group, member_id)
        policy.require_target(member)
        if payload.until and (
            timezone.is_naive(payload.until) or payload.until <= timezone.now()
        ):
            fail(
                "INVALID_EXPIRY",
                "Выберите будущую дату с часовым поясом.",
                422,
            )
        if payload.active:
            guard_last_manager(group, member)
        previous = GroupRestriction.objects.filter(
            group=group, user=member.user
        ).first()
        if previous and (previous.active, previous.until, previous.reason) == (
            payload.active,
            payload.until,
            payload.reason,
        ):
            return
        GroupRestriction.objects.update_or_create(
            group=group,
            user=member.user,
            defaults={
                "active": payload.active,
                "until": payload.until,
                "reason": payload.reason,
                "created_by": actor,
            },
        )
        if payload.active:
            member.status, member.role, member.left_at = (
                "removed",
                "member",
                timezone.now(),
            )
            member.save()
            close_all(group, actor, "Участие ограничено.", user=member.user)
            clean_pending(group)
        record(
            group,
            actor,
            "participation_restricted"
            if payload.active
            else "participation_restored",
            target=member.user,
            metadata=AuditMetadata(reason=payload.reason, until=payload.until),
        )
