from collections import defaultdict

from communities.access import authenticated
from communities.models import CommunityMembership
from django.db.models import Case, F, Prefetch, When
from profiles.policy import identity, visible

from cities.models import CityMembership
from cities.schemas import LeadershipOut


def public_leadership(cities, viewer, *, roles=("manager", "representative")):
    """Apply one audience policy to city pages and catalog cards in bulk."""
    result = defaultdict(list)
    if not cities:
        return result
    viewer_communities = set()
    if authenticated(viewer):
        viewer_communities = set(
            viewer.community_memberships.filter(
                status="active", community__status="active"
            ).values_list("community_id", flat=True)
        )
    members = (
        CityMembership.objects.filter(
            city__in=cities,
            status="active",
            role__in=roles,
            user__is_active=True,
            user__community_memberships__community_id=F("city__community_id"),
            user__community_memberships__status="active",
        )
        .select_related(
            "city", "user__community_profile", "user__extended_profile"
        )
        .prefetch_related(
            Prefetch(
                "user__community_memberships",
                queryset=CommunityMembership.objects.filter(status="active"),
                to_attr="hub_memberships",
            )
        )
        .order_by(
            "role",
            Case(When(position__iexact="Мэр", then=0), default=1),
            "position",
            "user__username",
        )
    )
    for member in members:
        own = authenticated(viewer) and viewer.pk == member.user_id
        if not visible(
            member.visibility,
            own=own,
            shared=member.city.community_id in viewer_communities,
        ):
            continue
        shared = viewer_communities & {
            m.community_id for m in member.user.hub_memberships
        }
        profile = getattr(member.user, "community_profile", None)
        if profile and not visible(
            profile.memberships_visibility, own=own, shared=shared
        ):
            continue
        result[member.city_id].append(
            LeadershipOut(
                **identity(member.user, viewer, shared=shared),
                role=member.role,
                position=member.position,
            )
        )
    return result
