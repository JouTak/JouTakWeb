from typing import Annotated

from accounts.transport.schemas import ErrorOut
from ninja import Query, Router, Schema
from profiles.schemas import CommunityMembershipOut, MembershipsOut, Slug
from profiles.services import memberships
from pydantic import Field

from communities.access import actor_for, require_flags
from communities.queries import (
    community_detail,
    community_out,
    community_queryset,
)
from communities.schemas import (
    CommunityListOut,
    CommunityOut,
    ServerMembershipsOut,
)

router = Router(tags=["Communities"])
membership_router = Router(tags=["Memberships"])
Page = Annotated[int, Field(ge=1, le=10000)]


class PageQuery(Schema):
    page: Page = 1


ERRORS = {401: ErrorOut, 404: ErrorOut, 422: ErrorOut}


@membership_router.get(
    "/server-communities", response={200: ServerMembershipsOut, **ERRORS}
)
def server_memberships(request):
    actor = actor_for(request, required=True)
    require_flags(actor, "communities_ui")
    return ServerMembershipsOut(
        items=[
            CommunityMembershipOut(
                community={"slug": m.community.slug, "name": m.community.name},
                role=m.role,
                status=m.status,
                joined_at=m.joined_at,
            )
            for m in actor.community_memberships.select_related(
                "community"
            ).order_by("community__name", "pk")
        ]
    )


@router.get("", response={200: CommunityListOut, **ERRORS})
def list_communities(request, filters: Query[PageQuery]):
    page = filters.page
    actor = actor_for(request)
    require_flags(actor, "communities_ui")
    query = community_queryset(actor)
    start = (page - 1) * 24
    return CommunityListOut(
        items=[community_out(c) for c in query[start : start + 24]],
        total=query.count(),
        page=page,
    )


@router.get("/{slug}", response={200: CommunityOut, **ERRORS})
def get_community(request, slug: Slug):
    actor = actor_for(request)
    require_flags(actor, "communities_ui")
    return community_detail(actor, slug)


@membership_router.get(
    "/memberships", response={200: MembershipsOut, **ERRORS}
)
def own_memberships(request):
    actor = actor_for(request, required=True)
    require_flags(actor, "communities_ui")
    return memberships(actor, actor)
