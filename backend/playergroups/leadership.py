from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from profiles.connections import accessible_players

from playergroups.common import locked_group, record
from playergroups.membership_service import target_id, target_member
from playergroups.models import GroupLeadershipOffer
from playergroups.participation import activate
from playergroups.policies import GroupPolicy, effective_members, fail
from playergroups.process_state import (
    clean_pending,
    close_process,
    process_status,
)
from playergroups.schemas import AuditMetadata


def offer(actor, slug, payload):
    with locked_group(
        slug, [actor.pk, target_id(slug, payload.membership_id)]
    ) as group:
        policy = GroupPolicy(actor, group)
        policy.require("configure")
        member = target_member(group, payload.membership_id)
        target_policy = GroupPolicy(member.user, group)
        if (
            not target_policy.role
            or member.role == "manager"
            or member.user_id == actor.pk
        ):
            fail(
                "INVALID_LEADERSHIP_TARGET",
                "Выберите другого действующего участника.",
                422,
            )
        if payload.transfer and policy.role != "manager":
            fail(
                "INVALID_TRANSFER",
                "Передать можно только свою роль руководителя.",
                422,
            )
        if group.status == "archived" or group.restricted:
            fail("UNAVAILABLE", "Сейчас передача руководства недоступна.")
        clean_pending(group)
        previous = GroupLeadershipOffer.objects.filter(
            group=group, user=member.user, status="pending"
        ).first()
        if previous:
            if (
                previous.offered_by_id != actor.pk
                or previous.transfer != payload.transfer
            ):
                fail("OFFER_EXISTS", "Участнику уже предложили руководство.")
            return previous
        process = GroupLeadershipOffer.objects.create(
            group=group,
            user=member.user,
            offered_by=actor,
            transfer=payload.transfer,
            expires_at=timezone.now()
            + timedelta(days=settings.GROUPS_INVITE_DAYS),
        )
        record(
            group,
            actor,
            "leadership_offered",
            target=member.user,
            metadata=AuditMetadata(process_id=process.pk),
        )
        return process


def respond(actor, offer_id, payload):
    initial = (
        GroupLeadershipOffer.objects.filter(pk=offer_id, user=actor)
        .select_related("group")
        .first()
    )
    if not initial:
        fail("OFFER_NOT_FOUND", "Предложение недоступно.", 404)
    with locked_group(
        initial.group.slug, [actor.pk, initial.offered_by_id]
    ) as group:
        process = GroupLeadershipOffer.objects.select_related(
            "offered_by", "user"
        ).get(pk=offer_id, user=actor)
        process.group = group
        desired = "accepted" if payload.decision == "accept" else "declined"
        if process.status == desired:
            return process
        if process_status(process) != "pending":
            fail("PROCESS_CLOSED", "Предложение уже недействительно.")
        if payload.decision == "accept":
            policy = GroupPolicy(actor, group)
            if (
                (not policy.role and not process.recovery)
                or not policy.eligible
                or policy.blocked
                or group.status == "archived"
                or (group.restricted and not process.recovery)
            ):
                fail(
                    "LEADERSHIP_UNAVAILABLE",
                    "Сейчас принять руководство нельзя.",
                )
            if (
                process.recovery
                and not GroupPolicy(process.offered_by, group).operator
            ):
                fail(
                    "LEADERSHIP_UNAVAILABLE",
                    "Предложение оператора недействительно.",
                )
            member = (
                activate(group, actor, actor, payload.visibility)
                if process.recovery
                else policy.membership
            )
            member.role = "manager"
            member.save(update_fields=["role", "updated_at"])
            if process.transfer:
                sender = group.memberships.get(
                    user=process.offered_by, status="active", role="manager"
                )
                sender.role = "member"
                sender.save(update_fields=["role", "updated_at"])
            if process.recovery:
                group.restricted = False
                group.accepting = False
                group.version += 1
                group.save()
            close_process(process, actor, "accepted")
            clean_pending(group)
        else:
            close_process(process, actor, "declined")
        return process


def revoke(actor, slug, offer_id):
    with locked_group(slug, [actor.pk]) as group:
        GroupPolicy(actor, group).require("configure")
        process = (
            GroupLeadershipOffer.objects.select_related("user")
            .filter(group=group, pk=offer_id)
            .first()
        )
        if not process:
            fail("OFFER_NOT_FOUND", "Предложение недоступно.", 404)
        process.group = group
        if process.status == "revoked":
            return process
        if process.status != "pending":
            fail("PROCESS_CLOSED", "Предложение уже завершено.")
        close_process(process, actor, "revoked")
        return process


def moderate(actor, slug, payload):
    with locked_group(slug, [actor.pk]) as group:
        GroupPolicy(actor, group).require("moderate")
        if (
            not payload.restricted
            and not effective_members(group).filter(role="manager").exists()
        ):
            fail(
                "LAST_MANAGER",
                "Сначала предложите руководство действующему участнику.",
            )
        if group.restricted == payload.restricted:
            return group
        group.restricted, group.moderation_reason = (
            payload.restricted,
            payload.reason,
        )
        group.accepting = False
        group.version += 1
        group.save()
        clean_pending(group)
        record(
            group,
            actor,
            "group_restricted" if payload.restricted else "group_unrestricted",
            metadata=AuditMetadata(reason=payload.reason),
        )
        return group


def recover(actor, slug, payload):
    target = get_user_model().objects.filter(username=payload.username).first()
    with locked_group(
        slug, [actor.pk, target.pk if target else None]
    ) as group:
        GroupPolicy(actor, group).require("moderate")
        if not group.restricted or group.status == "archived":
            fail(
                "RECOVERY_UNAVAILABLE",
                "Восстановление доступно для ограниченного объединения.",
            )
        member = (
            effective_members(group)
            .select_related("user")
            .filter(user__username=payload.username)
            .first()
        )
        target = (
            member.user
            if member
            else accessible_players(actor)
            .filter(username=payload.username)
            .first()
        )
        target_policy = GroupPolicy(target, group)
        if not target or not target_policy.eligible or target_policy.blocked:
            fail(
                "INVALID_LEADERSHIP_TARGET",
                "Игрок не соответствует условиям участия.",
                422,
            )
        clean_pending(group)
        if GroupLeadershipOffer.objects.filter(
            group=group, user=target, status="pending"
        ).exists():
            fail("OFFER_EXISTS", "Участнику уже предложили руководство.")
        process = GroupLeadershipOffer.objects.create(
            group=group,
            user=target,
            offered_by=actor,
            recovery=True,
            expires_at=timezone.now()
            + timedelta(days=settings.GROUPS_INVITE_DAYS),
        )
        record(
            group,
            actor,
            "leadership_recovery_offered",
            target=target,
            metadata=AuditMetadata(
                process_id=process.pk, reason=payload.reason
            ),
        )
        return process
