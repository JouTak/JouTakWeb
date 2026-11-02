from accounts.api.errors import raise_structured_error
from communities.models import Community, CommunityMembership
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from cities.audit import record_event, record_revision
from cities.models import City, CityContact, CityMembership
from cities.policies import CityPolicy, is_moderator
from cities.schemas import AuditMetadata


def fail(code, message, status=409):
    raise_structured_error(status, detail=message, error_code=code)


def find_city(slug, *, lock=False):
    query = City.objects.select_related("community")
    if lock:
        query = query.select_for_update(of=("self",))
    city = query.filter(slug=slug).first()
    if not city:
        fail("CITY_NOT_FOUND", "Город недоступен.", 404)
    return city


def apply_content(city, changes):
    contacts = changes.pop("contacts", None)
    if "location" in changes:
        location = changes.pop("location")
        if (
            location
            and not location["map_id"]
            and location["world"] == "overworld"
            and len(settings.ITMOCRAFT_MAP_IDS) == 1
        ):
            location["map_id"] = settings.ITMOCRAFT_MAP_IDS[0]
        if (
            location
            and location["map_id"]
            and location["map_id"] not in settings.ITMOCRAFT_MAP_IDS
        ):
            fail(
                "CITY_INVALID_MAP_LOCATION",
                "Карта не входит в список разрешённых.",
                422,
            )
        for field in ("world", "map_id", "x", "y", "z"):
            setattr(
                city,
                field,
                location[field]
                if location
                else (None if field in {"x", "y", "z"} else ""),
            )
    for field, value in changes.items():
        setattr(city, field, value)
    if city.status == "active" and not city.published_at:
        city.published_at = timezone.now()
    try:
        city.full_clean(validate_unique=False)
    except ValidationError:
        fail("CITY_INVALID_CONTENT", "Проверьте поля города.", 422)
    city.save()
    if contacts is not None:
        city.contacts.all().delete()
        CityContact.objects.bulk_create(
            [
                CityContact(city=city, sort_order=index, **contact)
                for index, contact in enumerate(contacts)
            ]
        )


@transaction.atomic
def create_city(actor, payload):
    if not is_moderator(actor):
        fail("CITY_PERMISSION_DENIED", "Требуются права модератора.", 403)
    manager = (
        get_user_model()
        .objects.select_for_update()
        .filter(
            username=payload.manager_username,
            is_active=True,
        )
        .first()
    )
    community = Community.objects.filter(
        slug=payload.community_slug,
        status="active",
    ).first()
    if not manager or not community:
        fail(
            "CITY_INVALID_MANAGER",
            "Сообщество или управляющий не найдены.",
            422,
        )
    if City.objects.filter(slug=payload.slug).exists():
        fail("CITY_SLUG_CONFLICT", "Этот адрес города уже занят.")
    membership, _ = CommunityMembership.objects.get_or_create(
        community=community,
        user=manager,
        defaults={"status": "active"},
    )
    if membership.status != "active":
        fail(
            "CITY_COMMUNITY_MEMBERSHIP_REQUIRED",
            "Управляющий должен быть участником сообщества.",
            422,
        )
    city = City(community=community, slug=payload.slug)
    changes = payload.model_dump(
        exclude={"slug", "community_slug", "manager_username"}
    )
    try:
        with transaction.atomic():
            apply_content(city, changes)
    except IntegrityError:
        fail("CITY_SLUG_CONFLICT", "Этот адрес города уже занят.")
    member = CityMembership.objects.create(
        city=city,
        user=manager,
        role="manager",
        status="active",
    )
    record_revision(city, actor, ["created"])
    record_event(city, actor, "CITY_CREATED")
    record_event(
        city,
        actor,
        "CITY_MEMBER_ADDED",
        member=member,
        metadata=AuditMetadata(after_role="manager", after_status="active"),
    )
    return city


@transaction.atomic
def update_city(actor, slug, payload):
    city = find_city(slug, lock=True)
    policy = CityPolicy(actor, city)
    policy.require("edit")
    if payload.version != city.version:
        fail(
            "CITY_VERSION_CONFLICT",
            "Город уже изменён. Обновите данные перед сохранением.",
        )
    changes = payload.model_dump(exclude_unset=True, exclude={"version"})
    if "status" in changes:
        policy.require("moderate")
        if (
            changes["status"] != "archived"
            and not city.memberships.filter(
                role="manager",
                status="active",
                user__is_active=True,
                user__community_memberships__community=city.community,
                user__community_memberships__status="active",
            ).exists()
        ):
            fail(
                "CITY_LAST_MANAGER",
                "Перед публикацией назначьте управляющего.",
            )
    representative_fields = {
        "name",
        "short_description",
        "description",
        "logo_url",
        "cover_url",
        "contacts",
        "how_to_join",
    }
    if (
        not policy.can_manage_members()
        and changes.keys() - representative_fields
    ):
        fail("CITY_PERMISSION_DENIED", "Это поле доступно управляющему.", 403)
    if not changes:
        return city
    changed_fields = sorted(changes)
    city.version += 1
    apply_content(city, changes)
    record_revision(city, actor, changed_fields)
    record_event(
        city,
        actor,
        "CITY_UPDATED",
        metadata=AuditMetadata(changed_fields=changed_fields),
    )
    return city
