"""Request-local policy/identity batches, never reused for mutations."""

from communities.models import CommunityMembership
from django.contrib.auth import get_user_model

from playergroups.models import GroupMembership
from playergroups.policies import active_restrictions, operator_users


class GroupReadContext:
    def __init__(self, groups, users, viewer=None):
        group_ids = {g.pk for g in groups}
        user_ids = {u.pk for u in users if u and u.is_authenticated}
        self.active = set(
            get_user_model()
            .objects.filter(pk__in=user_ids, is_active=True)
            .values_list("pk", flat=True)
        )
        self.operators = set(
            operator_users()
            .filter(pk__in=self.active)
            .values_list("pk", flat=True)
        )
        self.members = {
            (m.user_id, m.group_id): m
            for m in GroupMembership.objects.filter(
                user_id__in=user_ids, group_id__in=group_ids
            )
        }
        self.blocked = set(
            active_restrictions()
            .filter(user_id__in=user_ids, group_id__in=group_ids)
            .values_list("user_id", "group_id")
        )
        self.scopes = set(
            CommunityMembership.objects.filter(
                user_id__in=user_ids,
                status="active",
                community__status="active",
            ).values_list("user_id", "community_id")
        )
        viewer_scopes = {
            scope
            for user, scope in self.scopes
            if viewer and user == viewer.pk
        }
        self.shared_users = {
            user for user, scope in self.scopes if scope in viewer_scopes
        }

    @classmethod
    def for_processes(cls, processes, viewer):
        processes = list(processes)
        users = [viewer]
        for process in processes:
            users += [
                process.user,
                getattr(process, "invited_by", None),
                getattr(process, "offered_by", None),
            ]
        return cls([p.group for p in processes], users, viewer)

    def eligible(self, user, group):
        return bool(
            user
            and user.pk in self.active
            and (
                not group.scope_id or (user.pk, group.scope_id) in self.scopes
            )
        )
