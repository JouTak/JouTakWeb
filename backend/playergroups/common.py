import logging
from contextlib import contextmanager

from django.contrib.auth import get_user_model
from django.db import transaction

from playergroups.models import GroupAuditEvent, PlayerGroup
from playergroups.policies import fail, is_operator
from playergroups.schemas import AuditMetadata

logger = logging.getLogger(__name__)


def find_group(slug):
    group = (
        PlayerGroup.objects.select_related("scope").filter(slug=slug).first()
    )
    if not group:
        fail("NOT_FOUND", "Страница недоступна.", 404)
    return group


@contextmanager
def locked_group(slug, user_ids=()):
    with transaction.atomic():
        list(
            get_user_model()
            .objects.select_for_update(no_key=True)
            .filter(pk__in=[u for u in user_ids if u])
            .order_by("pk")
        )
        group = (
            PlayerGroup.objects.select_for_update(of=("self",))
            .select_related("scope")
            .filter(slug=slug)
            .first()
        )
        if not group:
            fail("NOT_FOUND", "Страница недоступна.", 404)
        yield group


def record(group, actor, action, *, target=None, metadata=None):
    metadata = (metadata or AuditMetadata()).model_copy(
        update={"platform_override": bool(is_operator(actor))}
    )
    GroupAuditEvent.objects.create(
        group=group,
        actor=actor,
        target=target,
        action=action,
        metadata=metadata.model_dump(mode="json", exclude_none=True),
    )
    logger.info(
        "group_id=%s actor_id=%s action=%s result=success",
        group.pk,
        getattr(actor, "pk", None),
        action,
    )
