from communities.access import authenticated
from django.db.models import BooleanField, Q, Value
from profiles.connections import accessible_players
from profiles.policy import identity, with_shared_community

from playergroups.common import find_group
from playergroups.policies import (
    GroupPolicy,
    active_restrictions,
    effective_members,
)
from playergroups.schemas import PeopleOut, PersonOut


def public_members(group, viewer, policy):
    query = effective_members(group).filter(
        user_id__in=accessible_players(viewer).values("pk")
    )
    query = (
        with_shared_community(query, viewer)
        if authenticated(viewer)
        else query.annotate(
            has_shared=Value(False, output_field=BooleanField())
        )
    )
    audience = ["public", "members"] if policy.role else ["public"]
    own = Q(user=viewer) if authenticated(viewer) else Q(pk__in=[])
    return query.filter(
        own
        | (
            Q(visibility__in=audience)
            & (
                Q(user__community_profile__memberships_visibility="public")
                | Q(
                    user__community_profile__memberships_visibility="community",
                    has_shared=True,
                )
            )
        )
    )


def people(viewer, slug, page, *, management=False, history=False):
    group = find_group(slug)
    policy = GroupPolicy(viewer, group)
    policy.require("manage" if management else "view")
    if management:
        query = group.memberships.all()
        if not history:
            query = query.filter(status="active")
        query = with_shared_community(query, viewer)
    else:
        visible = group.roster_visibility == "public" or (
            group.roster_visibility == "members" and bool(policy.role)
        )
        if not visible:
            return PeopleOut(items=[], total=None, page=page, is_visible=False)
        query = public_members(group, viewer, policy)
    query = query.select_related(
        "user__community_profile", "user__extended_profile"
    ).order_by("user__username", "pk")
    total = query.count()
    rows = list(query[(page - 1) * 24 : page * 24])
    blocked = (
        set(
            active_restrictions()
            .filter(group=group, user_id__in=[m.user_id for m in rows])
            .values_list("user_id", flat=True)
        )
        if management
        else set()
    )
    eligible_ids = (
        set(
            effective_members(group)
            .filter(pk__in=[m.pk for m in rows])
            .values_list("pk", flat=True)
        )
        if management
        else set()
    )
    result = []
    for member in rows:
        person = identity(member.user, viewer, shared=member.has_shared)
        result.append(
            PersonOut(
                id=member.pk if management else None,
                username=member.user.username
                if management
                else person.get("username"),
                minecraft_nick=person.get("minecraft_nick"),
                avatar_url=person.get("avatar_url"),
                role=member.role,
                status=member.status,
                visibility=member.visibility,
                restricted=member.user_id in blocked,
                eligible=member.pk in eligible_ids if management else True,
            )
        )
    return PeopleOut(items=result, total=total, page=page, is_visible=True)
