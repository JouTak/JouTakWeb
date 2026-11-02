from communities.models import Community, CommunityMembership
from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from playergroups.common import record
from playergroups.models import PlayerGroup
from playergroups.policies import effective_members, guard_last_manager
from playergroups.process_state import clean_pending, close_all
from playergroups.schemas import AuditMetadata


@receiver(pre_delete, sender=settings.AUTH_USER_MODEL)
def guard_user_deletion(sender, instance, origin=None, **kwargs):
    removed = (
        origin.values_list("pk", flat=True)
        if isinstance(origin, QuerySet)
        else []
    )
    for group in (
        PlayerGroup.objects.select_for_update()
        .filter(memberships__user=instance)
        .order_by("pk")
    ):
        member = group.memberships.get(user=instance)
        guard_last_manager(group, member, excluded_users=removed)
        # The deletion collector has already collected SET_NULL references.
        record(group, None, "account_removed")


@transaction.atomic
def end_dependent_memberships(user, *, scope_id=None):
    query = PlayerGroup.objects.filter(
        memberships__user=user, memberships__status="active"
    )
    if scope_id:
        query = query.filter(scope_id=scope_id)
    for group in query.select_for_update().order_by("pk"):
        member = group.memberships.get(user=user)
        member.status, member.role, member.left_at = (
            "removed",
            "member",
            timezone.now(),
        )
        member.save()
        close_all(group, None, "Условия участия изменились.", user=user)
        if (
            group.status != "archived"
            and not effective_members(group).filter(role="manager").exists()
        ):
            group.restricted, group.accepting = True, False
            group.moderation_reason = (
                "Требуется восстановление руководства после изменения "
                "аккаунта или серверного участия."
            )
            group.version += 1
            group.save()
            record(group, None, "governance_recovery_required")
        clean_pending(group)
        record(
            group,
            None,
            "participation_eligibility_lost",
            target=user,
            metadata=AuditMetadata(
                reason="Условия аккаунта или серверного участия изменились."
            ),
        )


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def handle_account_deactivation(sender, instance, **kwargs):
    if not instance.is_active:
        end_dependent_memberships(instance)


@receiver(post_save, sender=CommunityMembership)
def handle_scope_loss(sender, instance, **kwargs):
    if instance.status != "active":
        end_dependent_memberships(
            instance.user, scope_id=instance.community_id
        )


@receiver(post_save, sender=Community)
def handle_scope_archive(sender, instance, **kwargs):
    if instance.status != "active":
        for membership in (
            instance.memberships.select_related("user")
            .filter(status="active")
            .order_by("user_id")
        ):
            end_dependent_memberships(membership.user, scope_id=instance.pk)


@receiver(pre_delete, sender=CommunityMembership)
def handle_scope_delete(sender, instance, origin=None, **kwargs):
    if isinstance(origin, type(instance.user)) or (
        isinstance(origin, QuerySet) and origin.model is type(instance.user)
    ):
        return
    end_dependent_memberships(instance.user, scope_id=instance.community_id)
