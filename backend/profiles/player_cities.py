from collections import defaultdict

from cities.models import CityMembership
from communities.access import authenticated
from communities.models import CommunityMembership

from profiles.connection_schemas import PlayerCityOut
from profiles.policy import city_membership_visible, visible


def player_cities(players, viewer) -> dict[int, list[PlayerCityOut]]:
    """Load active city badges for a directory page in two queries."""
    if not players:
        return {}
    profiles = {player.pk: player.community_profile for player in players}
    viewer_id = viewer.pk if authenticated(viewer) else None
    user_ids = set(profiles)
    if viewer_id is not None:
        user_ids.add(viewer_id)
    communities = defaultdict(set)
    for user_id, community_id in CommunityMembership.objects.filter(
        user_id__in=user_ids, status="active", community__status="active"
    ).values_list("user_id", "community_id"):
        communities[user_id].add(community_id)
    result = defaultdict(list)
    memberships = (
        CityMembership.objects.filter(
            user_id__in=profiles,
            status="active",
            city__status="active",
            city__community__status="active",
        )
        .select_related("city__community")
        .order_by("city__name", "city__slug")
    )
    for membership in memberships:
        own = membership.user_id == viewer_id
        shared = communities[membership.user_id] & communities[viewer_id]
        if visible(
            profiles[membership.user_id].memberships_visibility,
            own=own,
            shared=shared,
        ) and city_membership_visible(
            membership,
            own=own,
            shared=shared,
            active_communities=communities[membership.user_id],
        ):
            result[membership.user_id].append(
                PlayerCityOut(
                    slug=membership.city.slug,
                    name=membership.city.name,
                    role=membership.role,
                    position=membership.position,
                )
            )
    return result
