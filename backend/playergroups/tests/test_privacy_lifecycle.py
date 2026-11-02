from datetime import timedelta
from types import SimpleNamespace

from communities.models import Community, CommunityMembership
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from profiles.models import CommunityProfile

from playergroups import leadership
from playergroups.account import own_processes, profile_groups
from playergroups.management_queries import processes
from playergroups.models import (
    GroupInvitation,
    GroupRestriction,
)
from playergroups.policies import GroupPolicy
from playergroups.queries import catalog
from playergroups.schemas import RecoveryIn, RespondIn
from playergroups.tests.test_workflows import GroupData


class PrivacyLifecycleTests(GroupData, TestCase):
    def test_revoked_platform_permission_is_not_taken_from_cached_actor(self):
        actor = self.users["operator"]
        self.assertTrue(GroupPolicy(actor, self.group).can_manage())
        get_user_model().objects.filter(pk=actor.pk).update(is_superuser=False)
        self.assertFalse(GroupPolicy(actor, self.group).can_manage())

    def test_orphan_recovery_requires_consent_and_keeps_recruitment_paused(
        self,
    ):
        self.group.memberships.update(status="removed", role="member")
        self.group.restricted = True
        self.group.accepting = False
        self.group.save()
        target = self.users["outside"]
        offer = leadership.recover(
            self.users["operator"],
            self.group.slug,
            RecoveryIn(
                username=target.username, reason="Руководство утрачено"
            ),
        )
        self.assertFalse(self.group.memberships.filter(user=target).exists())
        leadership.respond(target, offer.pk, RespondIn(decision="accept"))
        self.group.refresh_from_db()
        self.assertFalse(self.group.restricted)
        self.assertFalse(self.group.accepting)
        self.assertEqual(
            self.group.memberships.get(user=target).role, "manager"
        )
        event = self.group.audit_events.get(
            action="leadership_recovery_offered"
        )
        self.assertTrue(event.metadata["platform_override"])

    def test_group_membership_never_reveals_server_audience(self):
        self.group.roster_visibility = "public"
        self.group.save()
        self.group.memberships.update(visibility="public")
        member = self.users["member"]
        viewer = self.users["moderator"]
        CommunityProfile.objects.filter(user=member).update(
            memberships_visibility="community"
        )
        self.assertEqual(profile_groups(viewer, member.username, 1).total, 0)

    def test_member_audience_uses_effective_membership_for_both_people(self):
        target, viewer = self.users["member"], self.users["moderator"]
        self.group.memberships.filter(user=target).update(visibility="members")
        self.assertEqual(profile_groups(viewer, target.username, 1).total, 1)
        GroupRestriction.objects.create(
            group=self.group, user=viewer, active=True, reason="Проверка"
        )
        self.assertEqual(profile_groups(viewer, target.username, 1).total, 0)
        GroupRestriction.objects.all().delete()
        GroupRestriction.objects.create(
            group=self.group, user=target, active=True, reason="Проверка"
        )
        self.assertEqual(profile_groups(viewer, target.username, 1).total, 0)

    def test_scope_archive_reactivation_does_not_resurrect_roles(self):
        community = Community.objects.create(slug="server", name="Server")
        for user in self.users.values():
            CommunityMembership.objects.create(
                community=community, user=user, status="active"
            )
        self.group.scope = community
        self.group.save()
        community.status = "archived"
        community.save()
        self.assertFalse(
            self.group.memberships.filter(status="active").exists()
        )
        community.status = "active"
        community.save()
        self.assertFalse(
            self.group.memberships.filter(role="manager").exists()
        )
        self.group.refresh_from_db()
        self.assertTrue(self.group.restricted)

    def test_deleted_nonlast_manager_leaves_nullable_audit(self):
        second = self.group.memberships.get(user=self.users["member"])
        second.role = "manager"
        second.save()
        self.users["manager"].delete()
        self.assertTrue(
            self.group.audit_events.filter(
                action="account_removed", actor=None, target=None
            ).exists()
        )

    def test_private_scope_label_is_not_exposed_to_guests(self):
        community = Community.objects.create(
            slug="hidden-server", name="Secret", visibility="private"
        )
        self.group.scope = community
        self.group.save()
        result = catalog(
            None,
            SimpleNamespace(
                page=1, q="", scope=None, category=None, join_mode=None
            ),
            {},
        )
        self.assertIsNone(result.items[0].scope)


class QueryBudgetTests(GroupData, TestCase):
    def add_invitation(self, index):
        user = get_user_model().objects.create(username=f"invite_{index}")
        CommunityProfile.objects.create(user=user, visibility="public")
        GroupInvitation.objects.create(
            group=self.group,
            user=user,
            invited_by=self.users["manager"],
            expires_at=timezone.now() + timedelta(days=1),
        )

    def test_management_process_query_count_is_constant(self):
        self.add_invitation(0)
        # Warm only Django's user permission cache, not domain data.
        self.users["manager"].has_perm("playergroups.moderate_playergroup")
        with CaptureQueriesContext(connection) as small:
            processes(self.users["manager"], self.group.slug, 1, "invitation")
        for index in range(1, 10):
            self.add_invitation(index)
        with CaptureQueriesContext(connection) as large:
            result = processes(
                self.users["manager"], self.group.slug, 1, "invitation"
            )
        self.assertEqual(result.total, 10)
        self.assertEqual(len(small), len(large))
        self.assertLessEqual(len(large), 14)

    def test_inbox_query_count_is_constant_across_sender_profiles(self):
        user = self.users["outside"]
        for index in range(10):
            invitation = GroupInvitation.objects.create(
                group=self.group,
                user=user,
                invited_by=self.users["manager"],
                status="declined",
                expires_at=timezone.now() + timedelta(days=1),
            )
            if index == 0:
                with CaptureQueriesContext(connection) as small:
                    own_processes(user, 1, {})
        with CaptureQueriesContext(connection) as large:
            result = own_processes(user, 1, {})
        self.assertEqual(result.total, 10)
        self.assertEqual(len(small), len(large))
        self.assertEqual(invitation.status, "declined")
        self.assertLessEqual(len(large), 12)
