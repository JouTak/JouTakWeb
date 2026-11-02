from datetime import timedelta

from accounts.api.errors import StructuredHttpError
from communities.models import Community, CommunityMembership
from core.models import UserProfile
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase
from django.utils import timezone
from profiles.models import CommunityProfile
from profiles.policy import identity

from playergroups import (
    invitations,
    leadership,
    membership_service,
    participation,
    queries,
    services,
)
from playergroups.account import own_processes, profile_groups
from playergroups.models import (
    GroupAuditEvent,
    GroupMembership,
)
from playergroups.people import people
from playergroups.policies import GroupPolicy
from playergroups.schemas import (
    ApplyIn,
    GroupCreate,
    GroupUpdate,
    JoinIn,
    LifecycleIn,
    ModerationIn,
    OfferIn,
    RespondIn,
    RestrictionIn,
    ReviewIn,
    RoleIn,
)


class GroupData:
    @classmethod
    def setUpTestData(cls):
        cls.users = {}
        for role in ("manager", "moderator", "member", "outside", "operator"):
            user = get_user_model().objects.create_user(
                username=f"group_{role}",
                email=f"group_{role}@example.local",
                password="StrongPass123!",
                is_superuser=role == "operator",
            )
            CommunityProfile.objects.create(
                user=user,
                visibility="public",
                memberships_visibility="public",
                minecraft_visibility="community",
            )
            UserProfile.objects.create(user=user, minecraft_nick=f"Nick{role}")
            cls.users[role] = user
        cls.group = services.create_group(
            cls.users["manager"],
            GroupCreate(
                slug="builders",
                name="Мастерская",
                short_description="Строим вместе",
            ),
        )
        cls.group.status, cls.group.accepting, cls.group.join_mode = (
            "active",
            True,
            "open",
        )
        cls.group.save()
        for role in ("moderator", "member"):
            GroupMembership.objects.create(
                group=cls.group, user=cls.users[role], role=role
            )


class WorkflowTests(GroupData, TestCase):
    def assert_code(self, code, action):
        with self.assertRaises(StructuredHttpError) as raised:
            with transaction.atomic():
                action()
        self.assertEqual(
            raised.exception.payload["error_code"], f"GROUP_{code}"
        )

    def test_create_is_atomic_idempotent_and_has_no_external_roles(self):
        payload = GroupCreate(
            slug="new-club", name="Клуб", short_description="Описание"
        )
        group = services.create_group(self.users["outside"], payload)
        again = services.create_group(self.users["outside"], payload)
        self.assertEqual(group.pk, again.pk)
        self.assertEqual(group.memberships.count(), 1)
        self.assertEqual(group.audit_events.count(), 1)
        self.assertEqual(group.status, "draft")
        self.assertFalse(self.users["outside"].community_memberships.exists())

    def test_open_join_retry_leave_rejoin_and_privacy(self):
        user = self.users["outside"]
        participation.join(user, self.group.slug, JoinIn())
        member = self.group.memberships.get(user=user)
        joined = member.joined_at
        events = GroupAuditEvent.objects.count()
        participation.join(user, self.group.slug, JoinIn(visibility="public"))
        member.refresh_from_db()
        self.assertEqual(member.joined_at, joined)
        self.assertEqual(member.visibility, "private")
        self.assertEqual(GroupAuditEvent.objects.count(), events)
        member.role = "moderator"
        member.save()
        participation.leave(user, self.group.slug)
        participation.leave(user, self.group.slug)
        participation.join(user, self.group.slug, JoinIn())
        member.refresh_from_db()
        self.assertEqual(member.role, "member")
        self.assertIsNone(
            identity(user, self.users["member"]).get("minecraft_nick")
        )

    def test_last_manager_and_transfer_require_consent(self):
        manager, member = self.users["manager"], self.users["member"]
        self.assert_code(
            "LAST_MANAGER",
            lambda: participation.leave(manager, self.group.slug),
        )
        target = self.group.memberships.get(user=member)
        offer = leadership.offer(
            manager,
            self.group.slug,
            OfferIn(membership_id=target.pk, transfer=True),
        )
        self.assertEqual(GroupPolicy(member, self.group).role, "member")
        leadership.respond(member, offer.pk, RespondIn(decision="accept"))
        leadership.respond(member, offer.pk, RespondIn(decision="accept"))
        self.assertEqual(GroupPolicy(member, self.group).role, "manager")
        self.assertEqual(GroupPolicy(manager, self.group).role, "member")
        participation.leave(manager, self.group.slug)
        self.assertEqual(
            self.group.memberships.filter(
                role="manager", status="active"
            ).count(),
            1,
        )

    def test_requests_withdraw_review_and_idor(self):
        self.group.join_mode = "approval"
        self.group.application_question = "Чем хотите заниматься?"
        self.group.save()
        user = self.users["outside"]
        self.assert_code(
            "ANSWER_REQUIRED",
            lambda: participation.apply(user, self.group.slug, ApplyIn()),
        )
        pending = participation.apply(
            user, self.group.slug, ApplyIn(answer="Строить")
        )
        self.assertEqual(
            participation.apply(
                user, self.group.slug, ApplyIn(answer="Повтор")
            ).pk,
            pending.pk,
        )
        self.assertFalse(self.group.memberships.filter(user=user).exists())
        participation.decide_request(
            user, self.group.slug, pending.pk, withdraw=True
        )
        self.assert_code(
            "PROCESS_CLOSED",
            lambda: participation.decide_request(
                self.users["moderator"],
                self.group.slug,
                pending.pk,
                ReviewIn(decision="accept"),
            ),
        )
        pending = participation.apply(
            user, self.group.slug, ApplyIn(answer="Строить")
        )
        participation.decide_request(
            self.users["moderator"],
            self.group.slug,
            pending.pk,
            ReviewIn(decision="accept"),
        )
        self.assertEqual(self.group.memberships.get(user=user).role, "member")

    def test_invitation_and_request_resolve_together_without_duplicates(self):
        self.group.join_mode = "approval"
        self.group.save()
        user = self.users["outside"]
        application = participation.apply(user, self.group.slug, ApplyIn())
        invitation = invitations.invite(
            self.users["moderator"], self.group.slug, user.username
        )
        self.assertEqual(
            invitations.invite(
                self.users["moderator"], self.group.slug, user.username
            ).pk,
            invitation.pk,
        )
        self.assertFalse(self.group.memberships.filter(user=user).exists())
        self.assert_code(
            "INVITATION_NOT_FOUND",
            lambda: invitations.respond(
                self.users["member"],
                invitation.pk,
                RespondIn(decision="accept"),
            ),
        )
        invitations.respond(user, invitation.pk, RespondIn(decision="accept"))
        events = GroupAuditEvent.objects.count()
        invitations.respond(user, invitation.pk, RespondIn(decision="accept"))
        self.assertEqual(GroupAuditEvent.objects.count(), events)
        application.refresh_from_db()
        self.assertEqual(application.status, "accepted")
        self.assertEqual(self.group.memberships.filter(user=user).count(), 1)

    def test_inviter_loses_authority_and_cannot_grant_stale_access(self):
        invitation = invitations.invite(
            self.users["moderator"],
            self.group.slug,
            self.users["outside"].username,
        )
        membership_service.change_role(
            self.users["manager"],
            self.group.slug,
            self.group.memberships.get(user=self.users["moderator"]).pk,
            RoleIn(role="member"),
        )
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "revoked")
        self.assert_code(
            "PROCESS_CLOSED",
            lambda: invitations.respond(
                self.users["outside"],
                invitation.pk,
                RespondIn(decision="accept"),
            ),
        )

    def test_pause_archive_restore_and_expiry(self):
        user = self.users["outside"]
        invitation = invitations.invite(
            self.users["moderator"], self.group.slug, user.username
        )
        self.group.accepting = False
        self.group.save()
        self.assert_code(
            "JOIN_PAUSED",
            lambda: invitations.respond(
                user, invitation.pk, RespondIn(decision="accept")
            ),
        )
        self.group.accepting = True
        self.group.save()
        invitation.expires_at = timezone.now() - timedelta(seconds=1)
        invitation.save()
        self.assert_code(
            "PROCESS_CLOSED",
            lambda: invitations.respond(
                user, invitation.pk, RespondIn(decision="accept")
            ),
        )
        fresh = invitations.invite(
            self.users["moderator"], self.group.slug, user.username
        )
        self.assertNotEqual(fresh.pk, invitation.pk)
        group = services.lifecycle(
            self.users["manager"],
            self.group.slug,
            LifecycleIn(version=1, action="archive"),
        )
        fresh.refresh_from_db()
        self.assertEqual(fresh.status, "revoked")
        group = services.lifecycle(
            self.users["manager"],
            group.slug,
            LifecycleIn(version=group.version, action="restore"),
        )
        self.assertFalse(group.accepting)

    def test_private_preview_and_contacts_do_not_expand_access(self):
        self.group.access, self.group.join_mode = "private", "invite_only"
        self.group.save()
        self.group.contacts.create(
            type="telegram",
            label="Внутренний чат",
            url="https://t.me/privatechat",
            visibility="members",
        )
        user = self.users["outside"]
        invitation = invitations.invite(
            self.users["manager"], self.group.slug, user.username
        )
        self.assert_code(
            "NOT_FOUND", lambda: queries.detail(user, self.group.slug, {})
        )
        preview = own_processes(user, 1, {"player_groups_write": True})
        self.assertEqual(preview.items[0].group.name, self.group.name)
        self.assertNotIn("privatechat", preview.model_dump_json())
        invitations.revoke(
            self.users["manager"], self.group.slug, invitation.pk
        )
        self.assertIsNone(own_processes(user, 1, {}).items[0].group)

    def test_roster_and_profile_relationship_respect_personal_privacy(self):
        self.group.roster_visibility = "public"
        self.group.save()
        self.assertEqual(people(None, self.group.slug, 1).total, 0)
        member = self.group.memberships.get(user=self.users["member"])
        member.visibility = "public"
        member.save()
        roster = people(None, self.group.slug, 1)
        self.assertEqual(roster.total, 1)
        self.assertIsNone(roster.items[0].minecraft_nick)
        self.assertEqual(
            profile_groups(None, self.users["member"].username, 1).total, 1
        )
        self.group.access, self.group.join_mode = "private", "invite_only"
        self.group.save()
        self.assertEqual(
            profile_groups(None, self.users["member"].username, 1).total, 0
        )

    def test_moderator_cannot_escalate_or_remove_peers(self):
        moderator = self.users["moderator"]
        manager = self.group.memberships.get(user=self.users["manager"])
        self.assert_code(
            "PERMISSION_DENIED",
            lambda: membership_service.change_role(
                moderator, self.group.slug, manager.pk, RoleIn(role="member")
            ),
        )
        self.assert_code(
            "ROLE_PROTECTED",
            lambda: membership_service.remove_member(
                moderator, self.group.slug, manager.pk, ""
            ),
        )
        self.assert_code(
            "ROLE_PROTECTED",
            lambda: membership_service.remove_member(
                self.users["manager"], self.group.slug, manager.pk, ""
            ),
        )

    def test_restriction_blocks_every_entry_method_and_does_not_restore_role(
        self,
    ):
        user = self.users["member"]
        member = self.group.memberships.get(user=user)
        membership_service.restrict_member(
            self.users["moderator"],
            self.group.slug,
            member.pk,
            RestrictionIn(active=True, reason="Нарушение правил"),
        )
        self.assert_code(
            "PARTICIPATION_RESTRICTED",
            lambda: participation.join(user, self.group.slug, JoinIn()),
        )
        self.assert_code(
            "PARTICIPATION_RESTRICTED",
            lambda: invitations.invite(
                self.users["manager"], self.group.slug, user.username
            ),
        )
        membership_service.restrict_member(
            self.users["moderator"],
            self.group.slug,
            member.pk,
            RestrictionIn(active=False, reason="Ограничение снято"),
        )
        participation.join(user, self.group.slug, JoinIn())
        self.assertEqual(GroupPolicy(user, self.group).role, "member")

    def test_content_versions_and_group_settings_are_authorized(self):
        group = services.update_group(
            self.users["moderator"],
            self.group.slug,
            GroupUpdate(version=1, description="Новое"),
        )
        self.assertEqual(group.version, 2)
        self.assert_code(
            "VERSION_CONFLICT",
            lambda: services.update_group(
                self.users["moderator"],
                group.slug,
                GroupUpdate(version=1, description="Старое"),
            ),
        )
        self.assert_code(
            "PERMISSION_DENIED",
            lambda: services.update_group(
                self.users["moderator"],
                group.slug,
                GroupUpdate(version=2, accepting=False),
            ),
        )

    def test_account_deletion_deactivation_and_scope_loss_preserve_governance(
        self,
    ):
        manager = self.users["manager"]
        self.assert_code("LAST_MANAGER", lambda: manager.delete())
        manager.is_active = False
        manager.save()
        self.group.refresh_from_db()
        self.assertTrue(self.group.restricted)
        self.assertIsNone(GroupPolicy(manager, self.group).role)
        manager.is_active = True
        manager.save()
        self.assertIsNone(GroupPolicy(manager, self.group).role)

    def test_scope_loss_does_not_restore_privileged_membership(self):
        scope = Community.objects.create(slug="scope", name="Контекст")
        manager = self.users["manager"]
        context = CommunityMembership.objects.create(
            user=manager, community=scope, status="active"
        )
        group = services.create_group(
            manager,
            GroupCreate(
                slug="scoped",
                name="Команда",
                short_description="Общее дело",
                scope_slug=scope.slug,
            ),
        )
        context.status = "left"
        context.save()
        context.status = "active"
        context.save()
        group.refresh_from_db()
        self.assertTrue(group.restricted)
        self.assertIsNone(GroupPolicy(manager, group).role)

    def test_platform_restriction_is_separate_from_staff(self):
        user = self.users["outside"]
        user.is_staff = True
        user.save()
        self.assert_code(
            "PERMISSION_DENIED",
            lambda: leadership.moderate(
                user,
                self.group.slug,
                ModerationIn(restricted=True, reason="Проверка"),
            ),
        )
        leadership.moderate(
            self.users["operator"],
            self.group.slug,
            ModerationIn(restricted=True, reason="Проверка"),
        )
        self.group.refresh_from_db()
        self.assertFalse(
            GroupPolicy(self.users["manager"], self.group).can_manage()
        )
