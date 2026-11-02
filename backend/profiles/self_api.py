from communities.access import actor_for, require_flags
from ninja import Query, Router
from playergroups.account import profile_groups
from playergroups.schemas import GroupListOut

from profiles.api import ERRORS
from profiles.connection_schemas import (
    ConnectionFilters,
    FollowOut,
    PlayersOut,
)
from profiles.connections import connections
from profiles.following import (
    OwnFollowingOut,
    own_following,
    remove_own_follow,
)
from profiles.game_data import (
    GameDataOut,
    GameDataUpdate,
    read_game_data,
    save_game_data,
)
from profiles.preview import guest_preview
from profiles.schemas import ProfilePreviewOut
from profiles.social_api import actor as social_actor

router = Router(tags=["Profile editing"])


def owner(request):
    actor = actor_for(request, required=True)
    require_flags(actor, "community_profiles_ui")
    return actor


@router.get(
    "/me/preview",
    response={200: ProfilePreviewOut, **ERRORS},
    exclude_none=True,
)
def preview(request):
    return guest_preview(owner(request))


@router.get(
    "/me/preview/connections",
    response={200: PlayersOut, **ERRORS},
    exclude_none=True,
)
def preview_connections(request, filters: Query[ConnectionFilters]):
    actor = owner(request)
    return connections(actor.username, None, filters.direction, filters.page)


@router.get(
    "/me/preview/groups",
    response={200: GroupListOut, **ERRORS},
    exclude_none=True,
)
def preview_groups(request, filters: Query[ConnectionFilters]):
    actor = owner(request)
    require_flags(actor, "communities_ui", "player_groups_ui")
    return profile_groups(None, actor.username, filters.page)


@router.get("/me/game-data", response={200: GameDataOut, **ERRORS})
def get_game_data(request):
    return read_game_data(owner(request))


@router.patch("/me/game-data", response={200: GameDataOut, **ERRORS})
def update_game_data(request, payload: GameDataUpdate):
    return save_game_data(owner(request), payload)


@router.get("/me/following", response={200: OwnFollowingOut, **ERRORS})
def get_own_following(request, filters: Query[ConnectionFilters]):
    return own_following(owner(request), filters.page)


@router.delete(
    "/me/following/{relation_id}", response={200: FollowOut, **ERRORS}
)
def delete_own_follow(request, relation_id: int):
    return remove_own_follow(social_actor(request, required=True), relation_id)
