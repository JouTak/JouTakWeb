from typing import Annotated

from accounts.transport.schemas import ErrorOut, OkOut
from communities.access import actor_for, require_flags
from communities.api import PageQuery
from ninja import File, Query, Router, Schema, UploadedFile
from profiles.media import ImageOut, upload_image
from profiles.schemas import Slug
from pydantic import Field

from cities.catalog import catalog_cards
from cities.integrations.bluemap import location_from_url
from cities.membership_service import (
    change_member,
    set_membership_visibility,
)
from cities.models import City
from cities.policies import CityPolicy, is_moderator
from cities.queries import (
    detail,
    history,
    member_out,
    members,
    public_cities,
)
from cities.residents import residents
from cities.schemas import (
    CityDetailOut,
    CityListOut,
    CityUpdate,
    HistoryOut,
    LocationIn,
    MapLinkIn,
    MemberAdd,
    MemberListOut,
    MemberOut,
    MembershipVisibilityUpdate,
    MemberUpdate,
    OwnMembershipOut,
    ResidentsOut,
)
from cities.services import fail, find_city, update_city

router = Router(tags=["Cities"])
ERRORS = {
    401: ErrorOut,
    403: ErrorOut,
    404: ErrorOut,
    409: ErrorOut,
    422: ErrorOut,
}
MemberId = Annotated[int, Field(ge=1)]
Search = Annotated[str, Field(max_length=100)]


class CityFilters(PageQuery):
    q: Search = ""
    recruitment: City.Recruitment | None = None
    community: Slug | None = None


class RemovalQuery(Schema):
    override_reason: str = Field(default="", max_length=500)


def editor(request, *, moderation=False):
    actor = actor_for(request, required=True)
    flags = require_flags(actor, "cities_ui", "cities_management_ui")
    if moderation or is_moderator(actor):
        require_flags(actor, "cities_moderation_ui")
    return actor, flags


@router.post("/{slug}/map-location", response={200: LocationIn, **ERRORS})
def parse_map_location(request, slug: Slug, payload: MapLinkIn):
    actor, flags = editor(request)
    CityPolicy(actor, find_city(slug)).require("members")
    require_flags(actor, "cities_map_integration")
    return location_from_url(payload.url)


@router.post(
    "/{slug}/images", response={200: ImageOut, 429: ErrorOut, **ERRORS}
)
def upload_city_image(request, slug: Slug, file: File[UploadedFile]):
    actor, _ = editor(request)
    CityPolicy(actor, find_city(slug)).require("edit")
    return upload_image(request, actor, file)


@router.get("", response={200: CityListOut, **ERRORS})
def city_catalog(request, filters: Query[CityFilters]):
    q, recruitment, community, page = (
        filters.q,
        filters.recruitment,
        filters.community,
        filters.page,
    )
    actor = actor_for(request)
    flags = require_flags(actor, "cities_ui")
    query = public_cities(actor)
    if q:
        query = query.filter(name__icontains=q)
    if recruitment:
        query = query.filter(recruitment_status=recruitment)
    if community:
        query = query.filter(community__slug=community)
    start = (page - 1) * 24
    return CityListOut(
        items=catalog_cards(query[start : start + 24], actor, flags),
        total=query.count(),
        page=page,
    )


@router.get(
    "/{slug}", response={200: CityDetailOut, **ERRORS}, exclude_none=True
)
def city_detail(request, slug: Slug):
    actor = actor_for(request)
    flags = require_flags(actor, "cities_ui")
    return detail(actor, slug, flags)


@router.patch(
    "/{slug}", response={200: CityDetailOut, **ERRORS}, exclude_none=True
)
def city_update(request, slug: Slug, payload: CityUpdate):
    actor, flags = editor(
        request, moderation="status" in payload.model_fields_set
    )
    update_city(actor, slug, payload)
    return detail(actor, slug, flags)


@router.get("/{slug}/membership", response={200: OwnMembershipOut, **ERRORS})
def city_own_membership(request, slug: Slug):
    actor = actor_for(request, required=True)
    require_flags(actor, "cities_ui")
    city = find_city(slug)
    CityPolicy(actor, city).require("view")
    member = city.memberships.select_related("user").filter(user=actor).first()
    return OwnMembershipOut(
        membership=member_out(member, actor) if member else None
    )


@router.get(
    "/{slug}/residents",
    response={200: ResidentsOut, **ERRORS},
    exclude_none=True,
)
def city_residents(request, slug: Slug, filters: Query[PageQuery]):
    actor = actor_for(request)
    require_flags(actor, "cities_ui")
    return residents(actor, slug, filters.page)


@router.patch("/{slug}/membership", response={200: MemberOut, **ERRORS})
def city_membership_visibility(
    request, slug: Slug, payload: MembershipVisibilityUpdate
):
    actor = actor_for(request, required=True)
    require_flags(actor, "cities_ui")
    return member_out(
        set_membership_visibility(actor, slug, payload.visibility), actor
    )


@router.get("/{slug}/members", response={200: MemberListOut, **ERRORS})
def city_members(request, slug: Slug, filters: Query[PageQuery]):
    actor, _ = editor(request)
    return members(actor, slug, filters.page)


@router.post("/{slug}/members", response={200: MemberOut, **ERRORS})
def city_add_member(request, slug: Slug, payload: MemberAdd):
    actor, _ = editor(request, moderation=payload.role == "manager")
    CityPolicy(actor, find_city(slug)).require("members")
    fail(
        "CITY_INVITATION_REQUIRED",
        "Отправьте приглашение. Пользователь должен принять его "
        "в своём кабинете.",
    )


@router.patch(
    "/{slug}/members/{membership_id}", response={200: MemberOut, **ERRORS}
)
def city_change_member(
    request, slug: Slug, membership_id: MemberId, payload: MemberUpdate
):
    actor, _ = editor(
        request,
        moderation=payload.role == "manager" or bool(payload.override_reason),
    )
    return member_out(
        change_member(actor, slug, membership_id, payload), actor
    )


@router.delete(
    "/{slug}/members/{membership_id}", response={200: OkOut, **ERRORS}
)
def city_remove_member(
    request, slug: Slug, membership_id: MemberId, filters: Query[RemovalQuery]
):
    override_reason = filters.override_reason
    actor, _ = editor(request, moderation=bool(override_reason))
    change_member(
        actor,
        slug,
        membership_id,
        remove=True,
        override_reason=override_reason,
    )
    return OkOut(ok=True, message="Участник удалён из города.")


@router.get(
    "/{slug}/history", response={200: HistoryOut, **ERRORS}, exclude_none=True
)
def city_history(request, slug: Slug, filters: Query[PageQuery]):
    page = filters.page
    actor, _ = editor(request)
    return history(actor, slug, page)
