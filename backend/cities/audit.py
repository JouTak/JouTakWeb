import logging

from django.utils import timezone

from cities.models import City, CityAuditEvent, CityRevision
from cities.schemas import AuditMetadata, CityContent, ContactIn, LocationIn

logger = logging.getLogger(__name__)


def content_snapshot(city):
    location = None
    if city.x is not None:
        location = LocationIn(
            world=city.world,
            x=city.x,
            y=city.y,
            z=city.z,
            map_id=city.map_id,
        )
    return CityContent(
        **{
            key: getattr(city, key)
            for key in CityContent.model_fields
            if key not in {"contacts", "location"}
        },
        location=location,
        contacts=[
            ContactIn.model_validate(contact, from_attributes=True)
            for contact in city.contacts.all()
        ],
    )


def record_event(city, actor, action, *, metadata=None, member=None):
    city.updated_at = timezone.now()
    City.objects.filter(pk=city.pk).update(updated_at=city.updated_at)
    metadata = metadata or AuditMetadata()
    event = CityAuditEvent.objects.create(
        city=city,
        actor=actor,
        action=action,
        target_membership_id=member.pk if member else None,
        metadata=metadata.model_dump(mode="json", exclude_none=True),
    )
    logger.info(
        "city_id=%s city_slug=%s actor_id=%s action=%s result=success",
        city.pk,
        city.slug,
        actor.pk if actor else None,
        action,
    )
    return event


def record_revision(city, actor, fields):
    CityRevision.objects.create(
        city=city,
        actor=actor,
        version=city.version,
        content={
            **content_snapshot(city).model_dump(mode="json"),
            "status": city.status,
        },
        changed_fields=fields,
    )
