from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from cities.audit import record_event
from cities.models import City, CityMembership
from cities.policies import CityPolicy
from cities.schemas import AuditMetadata
from cities.services import fail, find_city


def guard_last_manager(
    city,
    member,
    *,
    override_reason="",
    moderator=False,
    removed_users=(),
    removed_members=(),
):
    if (
        member.status != "active"
        or member.role != "manager"
        or city.status == "archived"
    ):
        return
    other_managers = (
        city.memberships.filter(
            status="active",
            role="manager",
            user__is_active=True,
            user__community_memberships__community_id=city.community_id,
            user__community_memberships__status="active",
        )
        .exclude(pk=member.pk)
        .exclude(user_id__in=removed_users)
        .exclude(pk__in=removed_members)
        .exists()
    )
    if not other_managers and not (moderator and override_reason.strip()):
        fail("CITY_LAST_MANAGER", "Сначала назначьте другого управляющего.")


@transaction.atomic
def change_member(
    actor, slug, member_id, payload=None, *, remove=False, override_reason=""
):
    # Scope the initial lookup; check permission and re-read under lock.
    target_user = (
        CityMembership.objects.filter(city__slug=slug, pk=member_id)
        .values_list("user_id", flat=True)
        .first()
    )
    if target_user is not None:
        get_user_model().objects.select_for_update().filter(
            pk=target_user
        ).first()
    city = find_city(slug, lock=True)
    policy = CityPolicy(actor, city)
    policy.require("members")
    member = (
        city.memberships.select_related("user")
        .filter(pk=member_id, status="active")
        .first()
    )
    if not member:
        fail("CITY_MEMBER_NOT_FOUND", "Участник не найден.", 404)
    role = member.role if remove else payload.role
    reason = override_reason if remove else payload.override_reason
    if reason and not policy.moderator:
        fail(
            "CITY_PERMISSION_DENIED",
            "Override доступен только модератору.",
            403,
        )
    if not policy.moderator and (
        member.role == "manager" or role == "manager"
    ):
        fail(
            "CITY_INVALID_ROLE_CHANGE",
            "Роль управляющего меняет модератор.",
            403,
        )
    if remove or role != "manager":
        guard_last_manager(
            city, member, override_reason=reason, moderator=policy.moderator
        )
    before_role, before_status = member.role, member.status
    before_position = member.position
    if remove:
        member.status = "removed"
        member.left_at = timezone.now()
    else:
        member.role = role
        member.position = payload.position
    member.save()
    record_event(
        city,
        actor,
        "CITY_MEMBER_REMOVED" if remove else "CITY_ROLE_CHANGED",
        member=member,
        metadata=AuditMetadata(
            before_role=before_role,
            before_position=before_position,
            after_position=member.position,
            after_role=member.role,
            before_status=before_status,
            after_status=member.status,
            override_reason=reason or None,
        ),
    )
    return member


def guard_account_deletion(user, removed_users=()):
    # Called within Collector/account deletion transaction, including admin.
    get_user_model().objects.select_for_update().filter(pk=user.pk).first()
    city_ids = CityMembership.objects.filter(user=user).values_list(
        "city_id", flat=True
    )
    for city in (
        City.objects.select_for_update().filter(pk__in=city_ids).order_by("pk")
    ):
        member = city.memberships.get(user=user)
        guard_last_manager(city, member, removed_users=removed_users)
        record_event(city, None, "ACCOUNT_MEMBERSHIP_REMOVED", member=member)


@transaction.atomic
def set_membership_visibility(actor, slug, visibility):
    get_user_model().objects.select_for_update().get(pk=actor.pk)
    city = find_city(slug, lock=True)
    member = city.memberships.filter(user=actor, status="active").first()
    if not member:
        fail("CITY_MEMBER_NOT_FOUND", "Участник не найден.", 404)
    before_visibility = member.visibility
    member.visibility = visibility
    member.save(update_fields=["visibility", "updated_at"])
    record_event(
        city,
        actor,
        "CITY_MEMBERSHIP_VISIBILITY_CHANGED",
        member=member,
        metadata=AuditMetadata(
            before_visibility=before_visibility, after_visibility=visibility
        ),
    )
    return member
