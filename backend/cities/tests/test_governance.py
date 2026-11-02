from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from accounts.api.errors import StructuredHttpError
from communities.models import CommunityMembership
from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext
from profiles.models import CommunityProfile

from cities.invitations import invite, respond
from cities.membership_service import change_member
from cities.models import CityMembership
from cities.queries import detail
from cities.schemas import MemberUpdate
from cities.tests.test_hub import HubData


class GovernanceTests(HubData, TestCase):
    def test_bulk_user_deletion_cannot_remove_all_managers(self):
        CityMembership.objects.filter(
            city=self.city, user=self.users["representative"]
        ).update(role="manager")
        with self.assertRaises(StructuredHttpError), transaction.atomic():
            get_user_model().objects.filter(
                pk__in=[
                    self.users["manager"].pk,
                    self.users["representative"].pk,
                ]
            ).delete()
        self.assertEqual(
            self.city.memberships.filter(role="manager").count(), 2
        )

    def test_community_suspension_cannot_orphan_governance(self):
        membership = CommunityMembership.objects.get(
            user=self.users["manager"]
        )
        membership.status = "suspended"
        with self.assertRaises(StructuredHttpError):
            membership.save()
        membership.refresh_from_db()
        self.assertEqual(membership.status, "active")

    def test_staff_flag_alone_grants_no_city_power(self):
        user = self.users["outsider"]
        user.is_staff = True
        user.save()
        with self.assertRaises(StructuredHttpError):
            change_member(
                user,
                "alpha",
                self.city.memberships.get(role="resident").pk,
                MemberUpdate(role="representative"),
            )

    def test_hidden_leader_and_contacts_do_not_leak(self):
        leader = self.city.memberships.get(role="representative")
        leader.visibility = "public"
        leader.save()
        self.city.contacts.create(
            type="website",
            label="Internal",
            url="https://example.org",
            visibility="private",
        )
        data = detail(None, "alpha", {})
        self.assertEqual(data.contacts, [])
        self.assertEqual(
            data.leadership[0].display_name, "Участник сообщества"
        )
        self.assertIsNone(data.leadership[0].username)
        CommunityProfile.objects.create(
            user=leader.user,
            visibility="public",
            memberships_visibility="public",
        )
        self.assertEqual(
            detail(None, "alpha", {}).leadership[0].username, "representative"
        )
        CommunityMembership.objects.filter(user=leader.user).update(
            status="suspended"
        )
        self.assertEqual(detail(None, "alpha", {}).leadership, [])

    def test_profile_membership_privacy_applies_to_city_leadership(self):
        leader = self.city.memberships.get(role="representative")
        leader.visibility = "public"
        leader.save()
        profile = CommunityProfile.objects.create(
            user=leader.user,
            visibility="public",
            memberships_visibility="private",
        )
        self.assertEqual(detail(None, "alpha", {}).leadership, [])
        own = detail(leader.user, "alpha", {}).leadership
        self.assertIn("representative", [person.username for person in own])
        profile.memberships_visibility = "community"
        profile.save()
        self.assertEqual(detail(None, "alpha", {}).leadership, [])
        shared = detail(self.users["resident"], "alpha", {}).leadership
        self.assertIn("representative", [person.username for person in shared])

    def test_position_changes_have_before_and_after_audit(self):
        member = self.city.memberships.get(role="resident")
        change_member(
            self.users["manager"],
            "alpha",
            member.pk,
            MemberUpdate(role="representative", position="Дипломат"),
        )
        event = self.city.audit_events.first()
        self.assertEqual(event.metadata["before_position"], "")
        self.assertEqual(event.metadata["after_position"], "Дипломат")


class ConcurrentGovernanceTests(TransactionTestCase):
    # SQLite cannot prove this row-lock invariant; run on PostgreSQL.
    @skipUnlessDBFeature("has_select_for_update")
    def test_simultaneous_demotions_leave_one_manager(self):
        HubData.setUpTestData.__func__(self.__class__)
        second = CityMembership.objects.get(
            city=self.city, user=self.users["representative"]
        )
        second.role = "manager"
        second.save()
        first = self.city.memberships.get(user=self.users["manager"])
        barrier = Barrier(2)
        moderator_id = self.users["moderator"].pk

        def demote(member_id):
            close_old_connections()
            try:
                actor = get_user_model().objects.get(pk=moderator_id)
                barrier.wait(timeout=10)
                try:
                    change_member(
                        actor,
                        "alpha",
                        member_id,
                        MemberUpdate(role="resident"),
                    )
                    return "ok"
                except StructuredHttpError as exc:
                    return exc.payload["error_code"]
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(demote, [first.pk, second.pk]))
        self.assertCountEqual(results, ["ok", "CITY_LAST_MANAGER"])
        self.assertEqual(
            self.city.memberships.filter(
                role="manager", status="active"
            ).count(),
            1,
        )


class QueryBudgetTests(HubData, TestCase):
    def test_leadership_query_count_does_not_grow_per_person(self):
        with CaptureQueriesContext(connection) as small:
            detail(None, "alpha", {})
        for index in range(8):
            user = get_user_model().objects.create(username=f"leader_{index}")
            CommunityProfile.objects.create(
                user=user, visibility="public", memberships_visibility="public"
            )
            CommunityMembership.objects.create(
                user=user, community=self.community, status="active"
            )
            CityMembership.objects.create(
                user=user,
                city=self.city,
                status="active",
                role="representative",
                visibility="public",
            )
        with CaptureQueriesContext(connection) as large:
            detail(None, "alpha", {})
        self.assertEqual(len(small), len(large))
        self.assertLessEqual(len(large), 8)


class ConcurrentAccountDeletionTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_two_managers_cannot_delete_both_accounts(self):
        HubData.setUpTestData.__func__(self.__class__)
        CityMembership.objects.filter(
            city=self.city, user=self.users["representative"]
        ).update(role="manager")
        barrier = Barrier(2)

        def remove(user_id):
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=user_id)
                barrier.wait(timeout=10)
                try:
                    user.delete()
                    return "ok"
                except StructuredHttpError as exc:
                    return exc.payload["error_code"]
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(
                    remove,
                    [
                        self.users["manager"].pk,
                        self.users["representative"].pk,
                    ],
                )
            )
        self.assertCountEqual(results, ["ok", "CITY_LAST_MANAGER"])
        self.assertEqual(
            self.city.memberships.filter(
                role="manager", status="active"
            ).count(),
            1,
        )


class ConcurrentInvitationTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_two_acceptances_create_one_membership_and_one_audit(self):
        HubData.setUpTestData.__func__(self.__class__)
        invitation = invite(self.users["manager"], "alpha", "outsider")
        barrier = Barrier(2)
        recipient_id = self.users["outsider"].pk

        def accept(_index):
            close_old_connections()
            try:
                actor = get_user_model().objects.get(pk=recipient_id)
                barrier.wait(timeout=10)
                try:
                    respond(actor, invitation.id, "accept")
                    return "ok"
                except StructuredHttpError as exc:
                    return exc.payload["error_code"]
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(accept, [0, 1]))
        self.assertCountEqual(results, ["ok", "CITY_INVITATION_CLOSED"])
        self.assertEqual(
            self.city.memberships.filter(user_id=recipient_id).count(), 1
        )
        self.assertEqual(
            self.city.audit_events.filter(
                action="CITY_INVITATION_ACCEPTED"
            ).count(),
            1,
        )
