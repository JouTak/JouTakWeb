from accounts.transport.schemas import OkOut
from ninja import Query, Router
from profiles.schemas import Slug

from playergroups import (
    membership_service,
    participation,
    queries,
)
from playergroups.people import people
from playergroups.schemas import (
    GroupOut,
    JoinIn,
    PeopleOut,
    RemoveIn,
    RestrictionIn,
    RoleIn,
)

from .http import ERRORS, AccountFilters, Id, viewer

router = Router(tags=["Player groups"])


@router.get("/{slug}/members", response={200: PeopleOut, **ERRORS})
def management_roster(request, slug: Slug, filters: Query[AccountFilters]):
    actor, _ = viewer(request, required=True)
    return people(
        actor, slug, filters.page, management=True, history=filters.history
    )


@router.post("/{slug}/join", response={200: GroupOut, **ERRORS})
def join(request, slug: Slug, payload: JoinIn):
    actor, flags = viewer(request, write=True)
    participation.join(actor, slug, payload)
    return queries.detail(actor, slug, flags)


@router.post("/{slug}/leave", response={200: OkOut, **ERRORS})
def leave(request, slug: Slug):
    actor, _ = viewer(request, write=True)
    participation.leave(actor, slug)
    return OkOut(ok=True)


@router.patch("/{slug}/membership", response={200: OkOut, **ERRORS})
def visibility(request, slug: Slug, payload: JoinIn):
    actor, _ = viewer(request, write=True)
    participation.set_visibility(actor, slug, payload.visibility)
    return OkOut(ok=True)


@router.patch("/{slug}/members/{member_id}", response={200: OkOut, **ERRORS})
def member_role(request, slug: Slug, member_id: Id, payload: RoleIn):
    actor, _ = viewer(request, write=True)
    membership_service.change_role(actor, slug, member_id, payload)
    return OkOut(ok=True)


@router.post(
    "/{slug}/members/{member_id}/remove", response={200: OkOut, **ERRORS}
)
def member_remove(request, slug: Slug, member_id: Id, payload: RemoveIn):
    actor, _ = viewer(request, write=True)
    membership_service.remove_member(actor, slug, member_id, payload.reason)
    return OkOut(ok=True)


@router.post(
    "/{slug}/members/{member_id}/restriction", response={200: OkOut, **ERRORS}
)
def member_restrict(
    request, slug: Slug, member_id: Id, payload: RestrictionIn
):
    actor, _ = viewer(request, write=True)
    membership_service.restrict_member(actor, slug, member_id, payload)
    return OkOut(ok=True)
