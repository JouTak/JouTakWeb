from communities.api import PageQuery
from ninja import Query, Router

from playergroups import (
    account,
    invitations,
    leadership,
    participation,
)
from playergroups.models import GroupJoinRequest
from playergroups.policies import fail
from playergroups.schemas import (
    AccountGroupListOut,
    AccountProcessListOut,
    ProcessOut,
    RespondIn,
)
from playergroups.serializers import process_out

from .http import ERRORS, AccountFilters, Id, viewer

router = Router(tags=["Player groups"])


@router.get("/groups", response={200: AccountGroupListOut, **ERRORS})
def my_groups(request, filters: Query[AccountFilters]):
    actor, _ = viewer(request, required=True)
    return account.account_groups(actor, filters.page, filters.history)


@router.get(
    "/group-processes", response={200: AccountProcessListOut, **ERRORS}
)
def my_processes(request, filters: Query[PageQuery]):
    actor, flags = viewer(request, required=True)
    return account.own_processes(actor, filters.page, flags)


@router.post(
    "/group-invitations/{process_id}", response={200: ProcessOut, **ERRORS}
)
def respond_invitation(request, process_id: Id, payload: RespondIn):
    actor, _ = viewer(request, write=True)
    return process_out(
        invitations.respond(actor, process_id, payload), actor, "invitation"
    )


@router.post(
    "/group-requests/{process_id}/withdraw",
    response={200: ProcessOut, **ERRORS},
)
def withdraw_own_request(request, process_id: Id):
    actor, _ = viewer(request, write=True)
    process = (
        GroupJoinRequest.objects.filter(pk=process_id, user=actor)
        .select_related("group")
        .first()
    )
    if not process:
        fail("REQUEST_NOT_FOUND", "Заявка недоступна.", 404)
    return process_out(
        participation.decide_request(
            actor, process.group.slug, process_id, withdraw=True
        ),
        actor,
        "request",
    )


@router.post(
    "/group-leadership/{process_id}", response={200: ProcessOut, **ERRORS}
)
def respond_leadership(request, process_id: Id, payload: RespondIn):
    actor, _ = viewer(request, write=True)
    return process_out(
        leadership.respond(actor, process_id, payload), actor, "leadership"
    )
