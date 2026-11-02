from playergroups.common import find_group
from playergroups.models import PlayerGroup
from playergroups.policies import GroupPolicy, fail, is_operator
from playergroups.queries import process_queryset
from playergroups.read_context import GroupReadContext
from playergroups.schemas import (
    AuditListOut,
    AuditOut,
    GroupCardOut,
    GroupListOut,
    ProcessListOut,
)
from playergroups.serializers import group_ref, process_out


def processes(actor, slug, page, kind):
    group = find_group(slug)
    GroupPolicy(actor, group).require("manage")
    query = process_queryset(group, kind)
    rows = list(query[(page - 1) * 24 : page * 24])
    context = GroupReadContext.for_processes(rows, actor)
    return ProcessListOut(
        items=[process_out(p, actor, kind, context=context) for p in rows],
        total=query.count(),
        page=page,
    )


def history(actor, slug, page):
    group = find_group(slug)
    policy = GroupPolicy(actor, group)
    policy.require("view")
    if not policy.operator and policy.role != "manager":
        fail(
            "PERMISSION_DENIED",
            "История доступна руководству объединения.",
            403,
        )
    query = group.audit_events.select_related("actor", "target")
    return AuditListOut(
        items=[
            AuditOut(
                id=e.pk,
                action=e.action,
                actor=e.actor.username if e.actor else None,
                target=e.target.username if e.target else None,
                created_at=e.created_at,
                metadata=e.metadata,
            )
            for e in query[(page - 1) * 24 : page * 24]
        ],
        total=query.count(),
        page=page,
    )


def moderation(actor, page):
    if not is_operator(actor):
        fail(
            "PERMISSION_DENIED", "Нужны полномочия модератора платформы.", 403
        )
    query = PlayerGroup.objects.select_related("scope").order_by(
        "-updated_at", "pk"
    )
    return GroupListOut(
        items=[
            GroupCardOut(**group_ref(g).model_dump())
            for g in query[(page - 1) * 24 : page * 24]
        ],
        total=query.count(),
        page=page,
        can_moderate=True,
    )
