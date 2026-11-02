from communities.access import authenticated
from django.db.models import Q
from profiles.policy import identity

from cities.policies import CityPolicy
from cities.schemas import LeadershipOut, ResidentsOut
from cities.services import find_city


def residents(viewer, slug, page):
    city = find_city(slug)
    CityPolicy(viewer, city).require("view")
    shared = (
        authenticated(viewer)
        and viewer.community_memberships.filter(
            community=city.community, status="active"
        ).exists()
    )
    visibility = ["public", "community"] if shared else ["public"]
    own = Q(user=viewer) if authenticated(viewer) else Q(pk__in=[])
    query = (
        city.memberships.filter(
            status="active",
            user__is_active=True,
            user__community_memberships__community=city.community,
            user__community_memberships__status="active",
        )
        .filter(
            own
            | Q(
                visibility__in=visibility,
                user__community_profile__visibility__in=visibility,
                user__community_profile__memberships_visibility__in=visibility,
            )
        )
        .select_related("user__community_profile", "user__extended_profile")
        .order_by("user__username")
    )
    start = (page - 1) * 24
    return ResidentsOut(
        items=[
            LeadershipOut(
                **identity(m.user, viewer, shared=shared),
                role=m.role,
                position=m.position,
            )
            for m in query[start : start + 24]
        ],
        total=query.count(),
        page=page,
    )
