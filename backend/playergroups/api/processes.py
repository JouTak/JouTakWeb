from typing import Literal

from communities.api import PageQuery
from ninja import Query, Router
from profiles.schemas import Slug

from playergroups import (
    invitations,
    leadership,
    management_queries,
    participation,
)
from playergroups.schemas import (
    ApplyIn,
    InviteIn,
    OfferIn,
    ProcessListOut,
    ProcessOut,
    ReviewIn,
)
from playergroups.serializers import process_out

from .http import ERRORS, Id, viewer

router = Router(tags=["Player groups"])


@router.post("/{slug}/requests", response={200: ProcessOut, **ERRORS})
def apply(request, slug: Slug, payload: ApplyIn):
    actor, _ = viewer(request, write=True)
    return process_out(
        participation.apply(actor, slug, payload), actor, "request"
    )


@router.post(
    "/{slug}/requests/{process_id}/withdraw",
    response={200: ProcessOut, **ERRORS},
)
def withdraw(request, slug: Slug, process_id: Id):
    actor, _ = viewer(request, write=True)
    return process_out(
        participation.decide_request(actor, slug, process_id, withdraw=True),
        actor,
        "request",
    )


@router.post(
    "/{slug}/requests/{process_id}/decision",
    response={200: ProcessOut, **ERRORS},
)
def decide_request(request, slug: Slug, process_id: Id, payload: ReviewIn):
    actor, _ = viewer(request, write=True)
    return process_out(
        participation.decide_request(actor, slug, process_id, payload),
        actor,
        "request",
    )


@router.get("/{slug}/processes", response={200: ProcessListOut, **ERRORS})
def processes(
    request,
    slug: Slug,
    filters: Query[PageQuery],
    kind: Literal["invitation", "request", "leadership"] = "request",
):
    actor, _ = viewer(request, required=True)
    return management_queries.processes(actor, slug, filters.page, kind)


@router.post("/{slug}/invitations", response={200: ProcessOut, **ERRORS})
def invite(request, slug: Slug, payload: InviteIn):
    actor, _ = viewer(request, write=True)
    return process_out(
        invitations.invite(actor, slug, payload.username), actor, "invitation"
    )


@router.post(
    "/{slug}/invitations/{process_id}/revoke",
    response={200: ProcessOut, **ERRORS},
)
def revoke_invite(request, slug: Slug, process_id: Id):
    actor, _ = viewer(request, write=True)
    return process_out(
        invitations.revoke(actor, slug, process_id), actor, "invitation"
    )


@router.post("/{slug}/leadership", response={200: ProcessOut, **ERRORS})
def offer(request, slug: Slug, payload: OfferIn):
    actor, _ = viewer(request, write=True)
    return process_out(
        leadership.offer(actor, slug, payload), actor, "leadership"
    )


@router.post(
    "/{slug}/leadership/{process_id}/revoke",
    response={200: ProcessOut, **ERRORS},
)
def revoke_offer(request, slug: Slug, process_id: Id):
    actor, _ = viewer(request, write=True)
    return process_out(
        leadership.revoke(actor, slug, process_id), actor, "leadership"
    )
