from accounts.api.errors import raise_structured_error
from accounts.transport.schemas import ErrorOut
from communities.access import actor_for, require_flags
from decouple import config
from ninja import Query, Router

from backend.ratelimiting import ratelimit_method
from profiles.connection_schemas import (
    ConnectionFilters,
    FollowInput,
    FollowOut,
    PlayerFilters,
    PlayersOut,
)
from profiles.connections import connections, follow, search_players, unfollow
from profiles.contact_schemas import ContactsUpdate, SelfContactsOut
from profiles.contacts import save_contacts, self_contacts
from profiles.schemas import Username

router = Router(tags=["Player connections"])
ERRORS = {
    401: ErrorOut,
    403: ErrorOut,
    404: ErrorOut,
    409: ErrorOut,
    422: ErrorOut,
    429: ErrorOut,
}


def actor(request, *, required=False, mutate=False):
    user = actor_for(request, required=required)
    require_flags(user, "community_profiles_ui")
    if mutate and ratelimit_method(
        request,
        group="profiles.social",
        rate=config("RATELIMIT_PROFILE_SOCIAL", default="60/h"),
        key=lambda _group, _request: f"user:{user.pk}",
    ):
        raise_structured_error(
            429,
            detail="Слишком много изменений. Попробуйте позже.",
            error_code="PROFILE_RATE_LIMITED",
        )
    return user


@router.get(
    "/players", response={200: PlayersOut, **ERRORS}, exclude_none=True
)
def players(request, filters: Query[PlayerFilters]):
    return search_players(
        actor(request),
        filters.q.strip().removeprefix("@"),
        filters.page,
        filters.following,
    )


@router.get(
    "/public/{username}/connections",
    response={200: PlayersOut, **ERRORS},
    exclude_none=True,
)
def profile_connections(
    request, username: Username, filters: Query[ConnectionFilters]
):
    return connections(
        username, actor(request), filters.direction, filters.page
    )


@router.post("/public/{username}/follow", response={200: FollowOut, **ERRORS})
def follow_profile(request, username: Username, payload: FollowInput):
    return follow(actor(request, required=True, mutate=True), username)


@router.delete(
    "/public/{username}/follow", response={200: FollowOut, **ERRORS}
)
def unfollow_profile(request, username: Username):
    return unfollow(actor(request, required=True, mutate=True), username)


@router.get("/me/contacts", response={200: SelfContactsOut, **ERRORS})
def get_contacts(request):
    return self_contacts(actor(request, required=True))


@router.patch("/me/contacts", response={200: SelfContactsOut, **ERRORS})
def update_contacts(request, payload: ContactsUpdate):
    return save_contacts(actor(request, required=True, mutate=True), payload)
