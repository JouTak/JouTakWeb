from communities.api import PageQuery
from ninja import Query, Router
from profiles.schemas import Slug

from playergroups import (
    leadership,
    management_queries,
    queries,
)
from playergroups.schemas import (
    GroupListOut,
    GroupOut,
    ModerationIn,
    ProcessOut,
    RecoveryIn,
)
from playergroups.serializers import process_out

from .http import ERRORS, viewer

router = Router(tags=["Player groups"])


@router.get("", response={200: GroupListOut, **ERRORS})
def moderation_list(request, filters: Query[PageQuery]):
    actor, _ = viewer(request, required=True)
    return management_queries.moderation(actor, filters.page)


@router.post("/{slug}/restriction", response={200: GroupOut, **ERRORS})
def moderation_restrict(request, slug: Slug, payload: ModerationIn):
    actor, flags = viewer(request, write=True)
    leadership.moderate(actor, slug, payload)
    return queries.detail(actor, slug, flags)


@router.post("/{slug}/recovery", response={200: ProcessOut, **ERRORS})
def recovery(request, slug: Slug, payload: RecoveryIn):
    actor, _ = viewer(request, write=True)
    return process_out(
        leadership.recover(actor, slug, payload), actor, "leadership"
    )
