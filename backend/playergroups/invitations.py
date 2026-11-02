from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from profiles.connections import accessible_players

from playergroups.common import locked_group, record
from playergroups.models import GroupInvitation
from playergroups.participation import activate
from playergroups.policies import GroupPolicy, fail
from playergroups.process_state import (
    clean_pending,
    close_process,
    process_status,
)
from playergroups.schemas import AuditMetadata
from playergroups.services import require_join_target


def invite(actor, slug, username):
    user = accessible_players(actor).filter(username=username).first()
    with locked_group(slug, [actor.pk, getattr(user, "pk", None)]) as group:
        GroupPolicy(actor, group).require("manage")
        if not user:
            fail(
                "PLAYER_UNAVAILABLE", "Игрок недоступен для приглашения.", 404
            )
        require_join_target(user, group)
        if group.memberships.filter(user=user, status="active").exists():
            fail("ALREADY_MEMBER", "Игрок уже участвует в объединении.")
        clean_pending(group)
        existing = GroupInvitation.objects.filter(
            group=group, user=user, status="pending"
        ).first()
        if existing:
            return existing
        if GroupInvitation.objects.filter(
            group=group,
            user=user,
            status="declined",
            resolved_at__gt=timezone.now()
            - timedelta(days=settings.GROUPS_INVITE_COOLDOWN_DAYS),
        ).exists():
            fail(
                "INVITE_COOLDOWN",
                "Игрок недавно отказался. "
                "Повторное приглашение пока недоступно.",
            )
        if (
            GroupInvitation.objects.filter(
                invited_by=actor,
                created_at__gt=timezone.now() - timedelta(days=1),
            ).count()
            >= settings.GROUPS_INVITES_PER_DAY
        ):
            fail(
                "INVITE_LIMIT",
                "Лимит приглашений за сутки исчерпан. Попробуйте позже.",
                429,
            )
        process = GroupInvitation.objects.create(
            group=group,
            user=user,
            invited_by=actor,
            expires_at=timezone.now()
            + timedelta(days=settings.GROUPS_INVITE_DAYS),
        )
        record(
            group,
            actor,
            "invitation_sent",
            target=user,
            metadata=AuditMetadata(process_id=process.pk),
        )
        return process


def respond(actor, invitation_id, payload):
    invitation = (
        GroupInvitation.objects.filter(pk=invitation_id, user=actor)
        .select_related("group")
        .first()
    )
    if not invitation:
        fail("INVITATION_NOT_FOUND", "Приглашение недоступно.", 404)
    with locked_group(invitation.group.slug, [actor.pk]) as group:
        invitation = GroupInvitation.objects.select_related(
            "user", "invited_by"
        ).get(pk=invitation_id, user=actor)
        invitation.group = group
        desired = "accepted" if payload.decision == "accept" else "declined"
        if invitation.status == desired:
            return invitation
        if process_status(invitation) != "pending":
            fail(
                "PROCESS_CLOSED",
                "Приглашение завершено, отозвано или истекло.",
            )
        if payload.decision == "accept":
            require_join_target(actor, group)
            activate(group, actor, actor, payload.visibility)
            invitation.refresh_from_db()
        else:
            close_process(invitation, actor, "declined")
        return invitation


def revoke(actor, slug, invitation_id):
    with locked_group(slug, [actor.pk]) as group:
        GroupPolicy(actor, group).require("manage")
        invitation = (
            GroupInvitation.objects.filter(group=group, pk=invitation_id)
            .select_related("user")
            .first()
        )
        if not invitation:
            fail("INVITATION_NOT_FOUND", "Приглашение недоступно.", 404)
        invitation.group = group
        if invitation.status == "revoked":
            return invitation
        if invitation.status != "pending":
            fail("PROCESS_CLOSED", "Приглашение уже завершено.")
        close_process(
            invitation, actor, "revoked", "Организатор отозвал приглашение."
        )
        return invitation
