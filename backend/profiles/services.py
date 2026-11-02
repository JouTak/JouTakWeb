from accounts.api.errors import raise_structured_error
from cities.models import CityMembership
from cities.policies import is_moderator
from communities.access import authenticated
from communities.models import CommunityMembership
from django.contrib.auth import get_user_model
from django.db import transaction

from profiles.contacts import public_contacts
from profiles.editing import check_version, locked_profile
from profiles.models import CommunityProfile, ProfileFollow
from profiles.policy import (
    city_membership_visible,
    identity,
    shared_communities,
    visible,
)
from profiles.schemas import (
    CityMembershipOut,
    CommunityMembershipOut,
    CommunityRef,
    MembershipsOut,
    PublicProfileOut,
    SelfProfileOut,
)
from profiles.server_history import server_history


def memberships(subject, viewer, *, shared=None):
    own = authenticated(viewer) and subject.pk == viewer.pk
    shared = (
        shared if shared is not None else shared_communities(viewer, subject)
    )
    profile = getattr(subject, "community_profile", None)
    empty = MembershipsOut(communities=[], cities=[])
    if not own and (
        not profile
        or not visible(profile.memberships_visibility, shared=shared)
    ):
        return empty
    community_members = CommunityMembership.objects.filter(
        user=subject
    ).select_related("community")
    city_members = CityMembership.objects.filter(user=subject).select_related(
        "city__community"
    )
    if not own:
        community_members = community_members.filter(
            status="active", community__status="active"
        )
        city_members = city_members.filter(
            status="active",
            city__status="active",
            city__community__status="active",
        )
    community_ids = {
        m.community_id for m in community_members if m.status == "active"
    }
    community_out = [
        CommunityMembershipOut(
            community=CommunityRef(
                slug=m.community.slug, name=m.community.name
            ),
            role=m.role,
            status=m.status,
            joined_at=m.joined_at,
        )
        for m in community_members
        if own
        or m.community.visibility == "public"
        or m.community_id in shared
    ]
    city_out = [
        CityMembershipOut(
            slug=m.city.slug,
            name=m.city.name,
            logo_url=m.city.logo_url,
            short_description=m.city.short_description,
            community=CommunityRef(
                slug=m.city.community.slug, name=m.city.community.name
            ),
            status=m.status,
            city_status=m.city.status,
            role=m.role,
            position=m.position,
            visibility=m.visibility,
            joined_at=m.joined_at,
            can_manage=own
            and m.status == "active"
            and m.role in {"manager", "representative"}
            and m.city.community_id in community_ids
            and m.city.status != "archived",
        )
        for m in city_members
        if city_membership_visible(
            m, own=own, shared=shared, active_communities=community_ids
        )
    ]
    return MembershipsOut(communities=community_out, cities=city_out)


def profile_out(subject, viewer, *, self_view=False):
    profile = getattr(subject, "community_profile", None)
    shared = shared_communities(viewer, subject)
    own = authenticated(viewer) and viewer.pk == subject.pk
    if (
        not self_view
        and not own
        and (
            not subject.is_active
            or not profile
            or not visible(profile.visibility, shared=shared)
        )
    ):
        raise_structured_error(
            404, detail="Профиль недоступен.", error_code="PROFILE_NOT_FOUND"
        )
    if not profile:
        profile = CommunityProfile(user=subject)
    legacy = getattr(subject, "extended_profile", None)
    data = {
        **identity(subject, viewer, shared),
        "is_self": own,
        "is_following": authenticated(viewer)
        and ProfileFollow.objects.filter(user=viewer, target=subject).exists(),
        "contacts": public_contacts(subject, own=own, shared=shared),
        "username": subject.username,
        "display_name": profile.display_name or subject.username,
        "avatar_url": profile.avatar_url or None,
        "bio": profile.bio,
        "joined_at": subject.date_joined,
        "server_history": server_history(profile, own=own, shared=shared),
        "memberships": memberships(subject, viewer, shared=shared),
        "own_visibility": profile.visibility if own else None,
    }
    if legacy:
        if visible(profile.itmo_visibility, own=own, shared=shared):
            data["itmo_student"] = legacy.is_itmo_student
        if visible(profile.minecraft_visibility, own=own, shared=shared):
            data["minecraft_nick"] = legacy.minecraft_nick or None
    data["vk_url"] = next(
        (c.url for c in data["contacts"] if c.type == "vk"), None
    )
    if self_view:
        data["display_name"] = profile.display_name
        return SelfProfileOut(
            **data,
            version=profile.version,
            **{
                field: getattr(profile, field)
                for field in (
                    "visibility",
                    "minecraft_visibility",
                    "social_visibility",
                    "itmo_visibility",
                    "memberships_visibility",
                    "connections_visibility",
                )
            },
            can_moderate=is_moderator(viewer),
        )
    return PublicProfileOut(**data)


def public_profile(username, viewer):
    subject = (
        get_user_model()
        .objects.select_related("community_profile", "extended_profile")
        .filter(username=username, is_active=True)
        .first()
    )
    if not subject:
        raise_structured_error(
            404, detail="Профиль недоступен.", error_code="PROFILE_NOT_FOUND"
        )
    return profile_out(subject, viewer)


@transaction.atomic
def update_profile(user, payload):
    user = get_user_model().objects.select_for_update().get(pk=user.pk)
    profile = locked_profile(user)
    check_version(profile.version, payload.version)
    changes = payload.model_dump(exclude_unset=True, exclude={"version"})
    if (
        "social_visibility" in changes
        and changes["social_visibility"] != profile.social_visibility
        and profile.legacy_vk_enabled
    ):
        profile.contacts_version += 1
    for key, value in changes.items():
        setattr(profile, key, value)
    profile.full_clean()
    if changes:
        profile.version += 1
        profile.save(
            update_fields=[
                *changes,
                "version",
                "contacts_version",
                "updated_at",
            ]
        )
    user.community_profile = profile
    return profile_out(user, user, self_view=True)
