from django.utils import timezone

from playergroups.common import record
from playergroups.models import (
    GroupInvitation,
    GroupJoinRequest,
    GroupLeadershipOffer,
)
from playergroups.policies import GroupPolicy
from playergroups.schemas import AuditMetadata

PROCESS_MODELS = {
    "invitation": GroupInvitation,
    "request": GroupJoinRequest,
    "leadership": GroupLeadershipOffer,
}


def process_status(process, *, context=None):
    if process.status != "pending":
        return process.status
    if process.expires_at <= timezone.now():
        return "expired"
    if process.group.status == "archived":
        return (
            "cancelled" if isinstance(process, GroupJoinRequest) else "revoked"
        )
    sender = getattr(process, "invited_by", None) or getattr(
        process, "offered_by", None
    )
    if not isinstance(process, GroupJoinRequest):
        policy = GroupPolicy(sender, process.group, context=context)
        allowed = (
            policy.can_manage()
            if isinstance(process, GroupInvitation)
            else policy.can_configure()
        )
        if not allowed:
            return "revoked"
        if (
            isinstance(process, GroupLeadershipOffer)
            and process.transfer
            and policy.role != "manager"
        ):
            return "revoked"
    return "pending"


def close_process(process, actor, status, reason=""):
    if process.status == status:
        return
    process.status, process.reason, process.resolved_at = (
        status,
        reason,
        timezone.now(),
    )
    if isinstance(process, GroupJoinRequest):
        process.resolved_by = actor
    process.save()
    kind = next(
        k for k, model in PROCESS_MODELS.items() if isinstance(process, model)
    )
    record(
        process.group,
        actor,
        f"{kind}_{status}",
        # The process id links this transition to its original consent event.
        # Bulk closure must not acquire a new FK lock on an unrelated user
        # after locking the group (e.g. concurrent account deletion/archive).
        metadata=AuditMetadata(process_id=process.pk, reason=reason or None),
    )


def clean_pending(group):
    # Mutation-only cleanup; reads calculate expiry without a write.
    for model in PROCESS_MODELS.values():
        for process in model.objects.filter(
            group=group, status="pending"
        ).select_related(
            "group",
            "group__scope",
            "user",
            *(
                ["invited_by"]
                if model is GroupInvitation
                else ["offered_by"]
                if model is GroupLeadershipOffer
                else []
            ),
        ):
            status = process_status(process)
            if status != "pending":
                close_process(
                    process,
                    None,
                    status,
                    "Срок или условия предложения изменились.",
                )


def close_all(group, actor, reason, *, user=None):
    for model in PROCESS_MODELS.values():
        query = model.objects.filter(group=group, status="pending")
        if user:
            query = query.filter(user=user)
        for process in query.select_related("user"):
            process.group = group
            close_process(
                process,
                actor,
                "cancelled" if model is GroupJoinRequest else "revoked",
                reason,
            )
