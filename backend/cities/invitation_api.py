from accounts.transport.schemas import ErrorOut, OkOut
from communities.access import actor_for, require_flags
from communities.api import PageQuery
from ninja import Query, Router
from profiles.policy import with_shared_community
from profiles.schemas import Slug

from cities.api import ERRORS, MemberId, editor
from cities.invitations import (
    invitation_out,
    invite,
    pending_invitations,
    respond,
    revoke,
)
from cities.policies import CityPolicy
from cities.schemas import (
    InvitationIn,
    InvitationListOut,
    InvitationOut,
    InvitationResponse,
)
from cities.services import find_city

router = Router(tags=["City invitations"])
account_router = Router(tags=["My city invitations"])


def invitation_list(query, page, viewer):
    query = with_shared_community(query, viewer)
    start = (page - 1) * 24
    return InvitationListOut(
        items=[
            invitation_out(i, viewer, shared=i.has_shared)
            for i in query[start : start + 24]
        ],
        total=query.count(),
        page=page,
    )


@router.post("/{slug}/invitations", response={200: InvitationOut, **ERRORS})
def send_invitation(request, slug: Slug, payload: InvitationIn):
    actor, _ = editor(request)
    return invite(actor, slug, payload.username)


@router.get("/{slug}/invitations", response={200: InvitationListOut, **ERRORS})
def sent_invitations(request, slug: Slug, filters: Query[PageQuery]):
    actor, _ = editor(request)
    city = find_city(slug)
    CityPolicy(actor, city).require("members")
    return invitation_list(
        pending_invitations().filter(city=city), filters.page, actor
    )


@router.delete(
    "/{slug}/invitations/{invitation_id}", response={200: OkOut, **ERRORS}
)
def revoke_invitation(request, slug: Slug, invitation_id: MemberId):
    actor, _ = editor(request)
    revoke(actor, slug, invitation_id)
    return OkOut(ok=True, message="Приглашение отозвано.")


@account_router.get(
    "/city-invitations",
    response={
        200: InvitationListOut,
        401: ErrorOut,
        404: ErrorOut,
        422: ErrorOut,
    },
)
def my_invitations(request, filters: Query[PageQuery]):
    actor = actor_for(request, required=True)
    require_flags(actor, "cities_ui")
    return invitation_list(
        pending_invitations().filter(user=actor), filters.page, actor
    )


@account_router.post(
    "/city-invitations/{invitation_id}",
    response={200: InvitationOut, **ERRORS},
)
def answer_invitation(
    request, invitation_id: MemberId, payload: InvitationResponse
):
    actor = actor_for(request, required=True)
    require_flags(actor, "cities_ui")
    return respond(actor, invitation_id, payload.decision)
