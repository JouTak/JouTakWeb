"""Consent before membership. Lock order: user, city, invitation."""

from datetime import timedelta

from communities.models import CommunityMembership
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from profiles.policy import identity

from cities.audit import record_event
from cities.models import CityInvitation, CityMembership
from cities.policies import CityPolicy
from cities.schemas import AuditMetadata, InvitationOut
from cities.services import fail, find_city


def invitation_out(invitation, viewer, *, shared=None):
    person = identity(invitation.user, viewer, shared=shared)
    return InvitationOut(
        id=invitation.pk,
        city_slug=invitation.city.slug,
        city_name=invitation.city.name,
        logo_url=invitation.city.logo_url,
        username=invitation.user.username,
        minecraft_nick=person.get("minecraft_nick"),
        status=invitation.status,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
    )


def pending_invitations():
    return CityInvitation.objects.select_related(
        "city", "user__community_profile", "user__extended_profile"
    ).filter(
        status="pending",
        expires_at__gt=timezone.now(),
        city__status="active",
        city__community__status="active",
    )


def require_community(user, city):
    if (
        not user
        or not CommunityMembership.objects.filter(
            user=user,
            community=city.community,
            status="active",
        ).exists()
    ):
        fail(
            "CITY_COMMUNITY_MEMBERSHIP_REQUIRED",
            "Нужен активный участник сообщества.",
            422,
        )


@transaction.atomic
def invite(actor, slug, username):
    user = (
        get_user_model()
        .objects.select_for_update()
        .filter(username=username, is_active=True)
        .first()
    )
    city = find_city(slug, lock=True)
    CityPolicy(actor, city).require("members")
    if city.status != "active":
        fail(
            "CITY_INVITATION_UNAVAILABLE",
            "Приглашать можно в опубликованный город.",
        )
    require_community(user, city)
    if city.memberships.filter(user=user, status="active").exists():
        fail(
            "CITY_MEMBER_ALREADY_EXISTS",
            "Пользователь уже живёт в этом городе.",
        )
    city.invitations.filter(
        user=user, status="pending", expires_at__lte=timezone.now()
    ).update(status="revoked", responded_at=timezone.now())
    if city.invitations.filter(user=user, status="pending").exists():
        fail("CITY_INVITATION_EXISTS", "Приглашение уже отправлено.")
    invitation = CityInvitation.objects.create(
        city=city,
        user=user,
        invited_by=actor,
        expires_at=timezone.now() + timedelta(days=14),
    )
    record_event(
        city,
        actor,
        "CITY_INVITATION_SENT",
        metadata=AuditMetadata(invitation_id=invitation.pk),
    )
    return invitation_out(invitation, actor)


@transaction.atomic
def respond(actor, invitation_id, decision):
    get_user_model().objects.select_for_update().get(pk=actor.pk)
    invitation = CityInvitation.objects.filter(
        pk=invitation_id, user=actor
    ).first()
    if not invitation:
        fail("CITY_INVITATION_NOT_FOUND", "Приглашение недоступно.", 404)
    city = find_city(invitation.city.slug, lock=True)
    invitation = CityInvitation.objects.select_for_update().get(
        pk=invitation.pk
    )
    if (
        invitation.status != "pending"
        or invitation.expires_at <= timezone.now()
    ):
        fail("CITY_INVITATION_CLOSED", "Приглашение уже закрыто или истекло.")
    member = None
    if decision == "accept":
        if city.status != "active" or city.community.status != "active":
            fail(
                "CITY_INVITATION_UNAVAILABLE",
                "Приглашение в этот город больше недоступно.",
            )
        require_community(actor, city)
        member, _ = CityMembership.objects.get_or_create(city=city, user=actor)
        if member.status == "active":
            fail("CITY_MEMBER_ALREADY_EXISTS", "Вы уже живёте в этом городе.")
        member.status = "active"
        member.role = "resident"
        member.position = ""
        member.visibility = "community"
        member.joined_at = timezone.now()
        member.left_at = None
        member.save()
    invitation.status = "accepted" if decision == "accept" else "declined"
    invitation.responded_at = timezone.now()
    invitation.save(update_fields=["status", "responded_at"])
    record_event(
        city,
        actor,
        "CITY_INVITATION_ACCEPTED" if member else "CITY_INVITATION_DECLINED",
        member=member,
        metadata=AuditMetadata(invitation_id=invitation.pk),
    )
    return invitation_out(invitation, actor)


@transaction.atomic
def revoke(actor, slug, invitation_id):
    invitation = CityInvitation.objects.filter(
        pk=invitation_id, city__slug=slug
    ).first()
    if not invitation:
        fail("CITY_INVITATION_NOT_FOUND", "Приглашение недоступно.", 404)
    get_user_model().objects.select_for_update().get(pk=invitation.user_id)
    city = find_city(slug, lock=True)
    CityPolicy(actor, city).require("members")
    invitation = CityInvitation.objects.select_for_update().get(
        pk=invitation.pk
    )
    if invitation.status != "pending":
        fail("CITY_INVITATION_CLOSED", "Приглашение уже закрыто.")
    invitation.status = "revoked"
    invitation.responded_at = timezone.now()
    invitation.save(update_fields=["status", "responded_at"])
    record_event(
        city,
        actor,
        "CITY_INVITATION_REVOKED",
        metadata=AuditMetadata(invitation_id=invitation.pk),
    )
