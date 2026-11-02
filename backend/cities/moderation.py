from datetime import timedelta

from communities.api import PageQuery
from django.db.models import Prefetch
from django.utils import timezone
from ninja import Query, Router
from pydantic import Field

from cities.api import ERRORS, Search, editor
from cities.models import City, CityAuditEvent, CityMembership
from cities.policies import is_moderator
from cities.queries import card, cities_queryset, detail
from cities.schemas import (
    CityCreate,
    CityDetailOut,
    ModerationCityOut,
    ModerationListOut,
)
from cities.services import create_city, fail

router = Router(tags=["City moderation"])


class ModerationFilters(PageQuery):
    status: City.Status | None = None
    q: Search = ""
    recent_days: int | None = Field(default=None, ge=1, le=365)


@router.get("", response={200: ModerationListOut, **ERRORS})
def moderation_catalog(request, filters: Query[ModerationFilters]):
    status, q, page = filters.status, filters.q, filters.page
    actor, _ = editor(request, moderation=True)
    if not is_moderator(actor):
        fail("CITY_PERMISSION_DENIED", "Требуются права модератора.", 403)
    query = (
        cities_queryset()
        .order_by("-updated_at", "pk")
        .prefetch_related(
            Prefetch(
                "memberships",
                queryset=CityMembership.objects.filter(
                    status="active", role="manager"
                ).select_related("user"),
                to_attr="managers",
            ),
            Prefetch(
                "audit_events",
                queryset=CityAuditEvent.objects.select_related(
                    "actor"
                ).order_by("-created_at")[:1],
                to_attr="latest_events",
            ),
        )
    )
    if filters.recent_days is not None:
        query = query.filter(
            updated_at__gte=timezone.now()
            - timedelta(days=filters.recent_days)
        )
    if status:
        query = query.filter(status=status)
    if q:
        query = query.filter(name__icontains=q)
    start = (page - 1) * 24
    items = []
    for city in query[start : start + 24]:
        event = city.latest_events[0] if city.latest_events else None
        items.append(
            ModerationCityOut(
                **card(city).model_dump(),
                managers=[m.user.username for m in city.managers],
                updated_by=event.actor.username
                if event and event.actor
                else None,
                visibility=city.community.visibility,
            )
        )
    return ModerationListOut(items=items, total=query.count(), page=page)


@router.post("", response={200: CityDetailOut, **ERRORS}, exclude_none=True)
def moderation_create(request, payload: CityCreate):
    actor, flags = editor(request, moderation=True)
    city = create_city(actor, payload)
    return detail(actor, city.slug, flags)
