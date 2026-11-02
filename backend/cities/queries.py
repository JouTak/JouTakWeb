from communities.access import authenticated
from communities.queries import visible_communities
from django.db.models import Count, Q
from profiles.policy import identity, visible, with_shared_community
from profiles.schemas import CommunityRef

from cities.audit import content_snapshot
from cities.integrations.bluemap import map_url
from cities.leadership import public_leadership
from cities.models import City
from cities.policies import CityPolicy
from cities.schemas import (
    AuditOut,
    Capabilities,
    CityCardOut,
    CityDetailOut,
    HistoryOut,
    LocationOut,
    MemberListOut,
    MemberOut,
    RevisionOut,
)
from cities.services import find_city


def cities_queryset():
    return City.objects.select_related("community").annotate(
        member_count=Count(
            "memberships", filter=Q(memberships__status="active")
        ),
    )


def public_cities(user):
    return cities_queryset().filter(
        status="active", community__in=visible_communities(user)
    )


def card(city):
    return CityCardOut(
        slug=city.slug,
        name=city.name,
        short_description=city.short_description,
        logo_url=city.logo_url,
        status=city.status,
        recruitment_status=city.recruitment_status,
        community=CommunityRef(
            slug=city.community.slug, name=city.community.name
        ),
        member_count=city.member_count,
        updated_at=city.updated_at,
    )


def capabilities(policy, flags):
    enabled = flags.get("cities_management_ui", False) and (
        not policy.moderator or flags.get("cities_moderation_ui", False)
    )
    moderation = policy.moderator and flags.get("cities_moderation_ui", False)
    return Capabilities(
        edit=enabled and policy.can_edit(),
        manage_location=enabled and policy.can_manage_members(),
        manage_members=enabled and policy.can_manage_members(),
        manage_roles=enabled and policy.can_manage_members(),
        assign_manager=enabled and moderation,
        moderate=enabled and moderation,
    )


def detail(user, slug, flags):
    city = find_city(slug)
    policy = CityPolicy(user, city)
    policy.require("view")
    city.member_count = city.memberships.filter(status="active").count()
    content = content_snapshot(city)
    shared = bool(
        authenticated(user)
        and user.community_memberships.filter(
            community_id=city.community_id,
            status="active",
        ).exists()
    )
    leadership = public_leadership([city], user)[city.pk]
    location = None
    if content.location:
        location = LocationOut(
            **content.location.model_dump(),
            map_url=map_url(city)
            if flags.get("cities_map_integration")
            else None,
        )
    return CityDetailOut(
        **card(city).model_dump(),
        **content.model_dump(
            exclude={
                "name",
                "short_description",
                "logo_url",
                "recruitment_status",
                "contacts",
                "location",
            }
        ),
        location=location,
        contacts=[
            c
            for c in content.contacts
            if policy.can_edit() or visible(c.visibility, shared=shared)
        ],
        leadership=leadership,
        capabilities=capabilities(policy, flags),
        version=city.version,
        published_at=city.published_at,
    )


def member_out(member, viewer, *, shared=None):
    person = identity(member.user, viewer, shared=shared)
    return MemberOut(
        id=member.pk,
        username=member.user.username,
        minecraft_nick=person.get("minecraft_nick"),
        avatar_url=person.get("avatar_url"),
        role=member.role,
        position=member.position,
        status=member.status,
        visibility=member.visibility,
    )


def members(viewer, slug, page):
    city = find_city(slug)
    CityPolicy(viewer, city).require("members")
    query = with_shared_community(
        city.memberships.filter(status="active").select_related(
            "user__community_profile", "user__extended_profile"
        ),
        viewer,
    ).order_by("user__username")
    start = (page - 1) * 24
    return MemberListOut(
        items=[
            member_out(m, viewer, shared=m.has_shared)
            for m in query[start : start + 24]
        ],
        total=query.count(),
        page=page,
    )


def history(user, slug, page):
    city = find_city(slug)
    CityPolicy(user, city).require("edit")
    start = (page - 1) * 20
    events = city.audit_events.select_related("actor")[start : start + 20]
    revisions = city.revisions.select_related("actor")[start : start + 20]
    targets = dict(
        city.memberships.filter(
            pk__in=[e.target_membership_id for e in events]
        ).values_list("pk", "user__username")
    )
    invitation_targets = dict(
        city.invitations.filter(
            pk__in=[e.metadata.get("invitation_id") for e in events]
        ).values_list("pk", "user__username")
    )
    return HistoryOut(
        page=page,
        events=[
            AuditOut(
                id=e.pk,
                action=e.action,
                target_username=targets.get(e.target_membership_id)
                or invitation_targets.get(e.metadata.get("invitation_id")),
                actor=e.actor.username if e.actor else None,
                created_at=e.created_at,
                metadata=e.metadata,
            )
            for e in events
        ],
        revisions=[
            RevisionOut(
                version=r.version,
                actor=r.actor.username if r.actor else None,
                created_at=r.created_at,
                changed_fields=r.changed_fields,
                content=r.content,
            )
            for r in revisions
        ],
    )
