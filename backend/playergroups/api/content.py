from communities.api import PageQuery
from ninja import File, Query, Router, UploadedFile
from profiles.media import ImageOut, upload_image
from profiles.schemas import Slug

from playergroups import (
    management_queries,
    queries,
    services,
)
from playergroups.common import find_group
from playergroups.people import people
from playergroups.policies import GroupPolicy
from playergroups.schemas import (
    AuditListOut,
    GroupCreate,
    GroupListOut,
    GroupOut,
    GroupUpdate,
    LifecycleIn,
    PeopleOut,
)

from .http import ERRORS, Filters, viewer

router = Router(tags=["Player groups"])


@router.get("", response={200: GroupListOut, **ERRORS})
def catalog(request, filters: Query[Filters]):
    actor, flags = viewer(request)
    return queries.catalog(actor, filters, flags)


@router.post("", response={200: GroupOut, **ERRORS})
def create(request, payload: GroupCreate):
    actor, flags = viewer(request, write=True)
    group = services.create_group(actor, payload)
    return queries.detail(actor, group.slug, flags)


@router.get("/{slug}", response={200: GroupOut, **ERRORS})
def detail(request, slug: Slug):
    actor, flags = viewer(request)
    return queries.detail(actor, slug, flags)


@router.patch("/{slug}", response={200: GroupOut, **ERRORS})
def update(request, slug: Slug, payload: GroupUpdate):
    actor, flags = viewer(request, write=True)
    services.update_group(actor, slug, payload)
    return queries.detail(actor, slug, flags)


@router.post("/{slug}/lifecycle", response={200: GroupOut, **ERRORS})
def lifecycle(request, slug: Slug, payload: LifecycleIn):
    actor, flags = viewer(request, write=True)
    services.lifecycle(actor, slug, payload)
    return queries.detail(actor, slug, flags)


@router.post("/{slug}/images", response={200: ImageOut, **ERRORS})
def image(request, slug: Slug, file: File[UploadedFile]):
    actor, _ = viewer(request, write=True)
    GroupPolicy(actor, find_group(slug)).require("manage")
    return upload_image(request, actor, file)


@router.get("/{slug}/people", response={200: PeopleOut, **ERRORS})
def roster(request, slug: Slug, filters: Query[PageQuery]):
    actor, _ = viewer(request)
    return people(actor, slug, filters.page)


@router.get("/{slug}/history", response={200: AuditListOut, **ERRORS})
def history(request, slug: Slug, filters: Query[PageQuery]):
    actor, _ = viewer(request, required=True)
    return management_queries.history(actor, slug, filters.page)
