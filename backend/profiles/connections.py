from accounts.api.errors import raise_structured_error
from communities.access import authenticated
from communities.models import CommunityMembership
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import BooleanField, Exists, OuterRef, Q, Value
from django.db.models.functions import Lower

from profiles.connection_schemas import FollowOut, PlayerOut, PlayersOut
from profiles.models import ProfileFollow
from profiles.player_cities import player_cities
from profiles.policy import identity, shared_communities, visible

PAGE_SIZE = 24


def unavailable():
    raise_structured_error(
        404, detail="Профиль недоступен.", error_code="PROFILE_NOT_FOUND"
    )


def accessible_players(viewer):
    users = (
        get_user_model()
        .objects.filter(is_active=True)
        .select_related("community_profile", "extended_profile")
    )
    if authenticated(viewer):
        communities = CommunityMembership.objects.filter(
            user=viewer, status="active", community__status="active"
        ).values("community_id")
        shared = CommunityMembership.objects.filter(
            user_id=OuterRef("pk"),
            status="active",
            community_id__in=communities,
        )
        users = users.annotate(
            has_shared=Exists(shared),
            follows_viewer=Exists(
                ProfileFollow.objects.filter(
                    user=viewer, target_id=OuterRef("pk")
                )
            ),
        )
    else:
        users = users.annotate(
            has_shared=Value(False, output_field=BooleanField()),
            follows_viewer=Value(False, output_field=BooleanField()),
        )
    return users.filter(
        Q(community_profile__visibility="public")
        | Q(community_profile__visibility="community", has_shared=True)
    )


def allowed_connections():
    return Q(community_profile__connections_visibility="public") | Q(
        community_profile__connections_visibility="community", has_shared=True
    )


def page_out(users, viewer, page):
    total = users.count()
    rows = list(
        users.order_by(
            Lower("community_profile__display_name"), Lower("username"), "pk"
        )[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]
    )
    cities = player_cities(rows, viewer)
    return PlayersOut(
        items=[
            PlayerOut(
                **identity(user, viewer, shared=user.has_shared),
                bio=user.community_profile.bio[:160],
                cities=cities.get(user.pk, []),
                is_following=user.follows_viewer,
                is_self=authenticated(viewer) and viewer.pk == user.pk,
            )
            for user in rows
        ],
        total=total,
        page=page,
    )


def search_players(viewer, q, page, following):
    users = accessible_players(viewer)
    if following:
        if not authenticated(viewer):
            raise_structured_error(
                401,
                detail="Войдите, чтобы открыть свои подписки.",
                error_code="AUTH_REQUIRED",
            )
        users = users.filter(follows_viewer=True)
    if q:
        # Hidden nickname must not influence even an otherwise public result.
        nick_visible = Q(community_profile__minecraft_visibility="public") | Q(
            community_profile__minecraft_visibility="community",
            has_shared=True,
        )
        users = users.filter(
            Q(username__icontains=q)
            | Q(community_profile__display_name__icontains=q)
            | (nick_visible & Q(extended_profile__minecraft_nick__icontains=q))
        )
    return page_out(users, viewer, page)


def connections(username, viewer, direction, page):
    own = authenticated(viewer) and viewer.username == username
    subject = (
        get_user_model()
        .objects.select_related("community_profile")
        .filter(pk=viewer.pk)
        .first()
        if own
        else accessible_players(viewer).filter(username=username).first()
    )
    if not subject:
        unavailable()
    profile = getattr(subject, "community_profile", None)
    shared = shared_communities(viewer, subject)
    if not own and (
        not profile
        or not visible(profile.connections_visibility, shared=shared)
    ):
        return PlayersOut(items=[], total=0, page=page, is_visible=False)
    users = accessible_players(viewer)
    outgoing = ProfileFollow.objects.filter(user=subject).values("target_id")
    if direction == "following":
        users = users.filter(pk__in=outgoing)
    else:
        users = users.filter(
            pk__in=ProfileFollow.objects.filter(target=subject).values(
                "user_id"
            )
        ).filter(
            allowed_connections()
            | Q(pk=viewer.pk if authenticated(viewer) else None)
        )
        # Mutual follows become friends; the follower card contains one-way
        # incoming follows only. Both counts use the same visibility filters.
        users = (
            users.filter(pk__in=outgoing)
            if direction == "friends"
            else users.exclude(pk__in=outgoing)
        )
    return page_out(users, viewer, page)


@transaction.atomic
def follow(actor, username):
    # Lock both users in stable order, including against account deletion.
    locked = list(
        get_user_model()
        .objects.select_for_update()
        .filter(Q(pk=actor.pk) | Q(username=username))
        .order_by("pk")
    )
    target = next((user for user in locked if user.username == username), None)
    if (
        not target
        or not accessible_players(actor).filter(pk=target.pk).exists()
    ):
        unavailable()
    if target.pk == actor.pk:
        raise_structured_error(
            422,
            detail="Нельзя подписаться на себя.",
            error_code="PROFILE_SELF_FOLLOW",
        )
    ProfileFollow.objects.get_or_create(user=actor, target=target)
    return FollowOut(is_following=True)


@transaction.atomic
def unfollow(actor, username):
    # Hidden/deactivated targets can be unfollowed without revealing existence.
    list(
        get_user_model()
        .objects.select_for_update()
        .filter(Q(pk=actor.pk) | Q(username=username))
        .order_by("pk")
    )
    ProfileFollow.objects.filter(
        user=actor, target__username=username
    ).delete()
    return FollowOut(is_following=False)
