from communities.access import authenticated
from communities.models import CommunityMembership
from django.db.models import Exists, OuterRef


def with_shared_community(query, viewer):
    """Annotate rows having user_id without per-player audience queries."""
    viewer_communities = CommunityMembership.objects.filter(
        user=viewer, status="active", community__status="active"
    ).values("community_id")
    return query.annotate(
        has_shared=Exists(
            CommunityMembership.objects.filter(
                user_id=OuterRef("user_id"),
                status="active",
                community_id__in=viewer_communities,
            )
        )
    )


def shared_communities(viewer, subject):
    if not authenticated(viewer):
        return set()
    return set(
        CommunityMembership.objects.filter(
            user=viewer,
            status="active",
            community__status="active",
            community__memberships__user=subject,
            community__memberships__status="active",
        ).values_list("community_id", flat=True)
    )


def visible(visibility, *, own=False, shared=False):
    return (
        own
        or visibility == "public"
        or (visibility == "community" and bool(shared))
    )


def city_membership_visible(membership, *, own, shared, active_communities):
    community = membership.city.community
    return own or (
        community.pk in active_communities
        and visible(membership.visibility, shared=community.pk in shared)
        and (community.visibility == "public" or community.pk in shared)
    )


def identity(user, viewer, shared=None):
    profile = getattr(user, "community_profile", None)
    own = authenticated(viewer) and viewer.pk == user.pk
    if shared is None:
        shared = shared_communities(viewer, user)
    if not profile or not visible(profile.visibility, own=own, shared=shared):
        return {"display_name": "Участник сообщества"}
    legacy = getattr(user, "extended_profile", None)
    result = {
        "username": user.username,
        "display_name": profile.display_name or user.username,
        "avatar_url": profile.avatar_url or None,
    }
    if legacy and visible(
        profile.minecraft_visibility, own=own, shared=shared
    ):
        result["minecraft_nick"] = legacy.minecraft_nick or None
    return result
