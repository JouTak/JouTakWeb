from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from accounts.api.errors import StructuredHttpError
from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import TransactionTestCase, skipUnlessDBFeature

from playergroups import invitations, participation, services
from playergroups.schemas import JoinIn, LifecycleIn, RespondIn
from playergroups.tests.test_workflows import GroupData


class ConcurrentGroupsTests(TransactionTestCase):
    def setUp(self):
        super().setUp()
        GroupData.setUpTestData.__func__(self.__class__)

    def parallel(self, work):
        barrier = Barrier(2)

        def execute(item):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    item()
                    return "ok"
                except StructuredHttpError as exc:
                    return exc.payload["error_code"]
            finally:
                connection.close()

        def start(item):
            return execute(item)

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(start, work))

    @skipUnlessDBFeature("has_select_for_update")
    def test_two_managers_leaving_preserves_one(self):
        self.group.memberships.filter(user=self.users["member"]).update(
            role="manager"
        )
        ids = [self.users[role].pk for role in ("manager", "member")]

        def leave(pk):
            participation.leave(
                get_user_model().objects.get(pk=pk), self.group.slug
            )

        results = self.parallel([lambda: leave(ids[0]), lambda: leave(ids[1])])
        self.assertCountEqual(results, ["ok", "GROUP_LAST_MANAGER"])
        self.assertEqual(
            self.group.memberships.filter(
                role="manager", status="active"
            ).count(),
            1,
        )

    @skipUnlessDBFeature("has_select_for_update")
    def test_two_join_clicks_have_one_membership_and_audit(self):
        actor_id = self.users["outside"].pk

        def join():
            participation.join(
                get_user_model().objects.get(pk=actor_id),
                self.group.slug,
                JoinIn(),
            )

        self.assertEqual(self.parallel([join, join]), ["ok", "ok"])
        self.assertEqual(
            self.group.memberships.filter(user_id=actor_id).count(), 1
        )
        self.assertEqual(
            self.group.audit_events.filter(
                action="member_joined", target_id=actor_id
            ).count(),
            1,
        )

    @skipUnlessDBFeature("has_select_for_update")
    def test_accept_invitation_against_archive_is_serialized(self):
        invitation = invitations.invite(
            self.users["manager"],
            self.group.slug,
            self.users["outside"].username,
        )

        def accept():
            invitations.respond(
                get_user_model().objects.get(pk=self.users["outside"].pk),
                invitation.pk,
                RespondIn(decision="accept"),
            )

        def archive():
            services.lifecycle(
                get_user_model().objects.get(pk=self.users["manager"].pk),
                self.group.slug,
                LifecycleIn(version=1, action="archive"),
            )

        results = self.parallel([accept, archive])
        self.assertEqual(results[1], "ok")
        self.assertIn(results[0], ["ok", "GROUP_PROCESS_CLOSED"])
        invitation.refresh_from_db()
        self.group.refresh_from_db()
        self.assertEqual(self.group.status, "archived")
        self.assertIn(invitation.status, ["accepted", "revoked"])
