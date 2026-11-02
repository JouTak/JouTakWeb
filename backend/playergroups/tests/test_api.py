from unittest.mock import patch

from accounts.tests.base import APITestCase
from featureflags.registry import HUB_FLAG_KEYS

from playergroups import invitations, services
from playergroups.models import GroupAuditEvent, PlayerGroup
from playergroups.schemas import GroupCreate
from playergroups.tests.test_workflows import GroupData


class GroupAPITests(GroupData, APITestCase):
    def setUp(self):
        super().setUp()
        flags = patch(
            "communities.access.flags_for",
            return_value=dict.fromkeys(HUB_FLAG_KEYS, True),
        )
        flags.start()
        self.addCleanup(flags.stop)

    def headers(self, role):
        response = self.login(email=self.users[role].email)
        self.assertEqual(response.status_code, 200, response.content)
        return self.auth_headers(self.session_token(response))

    def test_guest_reads_and_private_enumeration(self):
        self.assertEqual(self.client.get("/api/groups").status_code, 200)
        response = self.client.get("/api/groups/builders")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(response.json()["capabilities"]["edit"])
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertIsNone(
            self.client.get("/api/groups/builders/people").json()["total"]
        )
        self.assertEqual(
            self.post_json("/groups/builders/join").status_code, 401
        )
        for state in ["draft", "archived"]:
            PlayerGroup.objects.filter(pk=self.group.pk).update(status=state)
            self.assertEqual(
                self.client.get("/api/groups/builders").status_code, 404
            )
        PlayerGroup.objects.filter(pk=self.group.pk).update(
            status="active", access="private", join_mode="invite_only"
        )
        self.assertEqual(
            self.client.get("/api/groups/builders").status_code, 404
        )
        self.assertEqual(
            self.client.get("/api/groups/no-such-group").json()["error_code"],
            self.client.get("/api/groups/builders").json()["error_code"],
        )

    def test_permission_validation_and_scoped_ids(self):
        member_headers = self.headers("member")
        self.assertEqual(
            self.patch_json(
                "/groups/builders",
                {"version": 1, "description": "wrong"},
                **member_headers,
            ).status_code,
            403,
        )
        moderator_headers = self.headers("moderator")
        self.assertEqual(
            self.patch_json(
                "/groups/builders",
                {"version": 1, "description": "allowed"},
                **moderator_headers,
            ).status_code,
            200,
        )
        self.assertEqual(
            self.patch_json(
                "/groups/builders",
                {"version": 2, "access": "unlisted"},
                **moderator_headers,
            ).status_code,
            403,
        )
        manager_headers = self.headers("manager")
        member = self.group.memberships.get(user=self.users["member"])
        for role in ["manager", "PLATFORM_ADMIN"]:
            self.assertEqual(
                self.patch_json(
                    f"/groups/builders/members/{member.pk}",
                    {"role": role},
                    **manager_headers,
                ).status_code,
                422,
            )
        other = services.create_group(
            self.users["outside"],
            GroupCreate(
                slug="other", name="Другие", short_description="Другая группа"
            ),
        )
        foreign = other.memberships.get()
        response = self.patch_json(
            f"/groups/builders/members/{foreign.pk}",
            {"role": "moderator"},
            **manager_headers,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            self.client.get(
                "/api/groups/builders/history", **member_headers
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                "/api/moderation/groups", **member_headers
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                "/api/moderation/groups", **self.headers("operator")
            ).status_code,
            200,
        )

    def test_invitation_consent_recipient_scope_retry_and_inbox(self):
        manager = self.users["manager"]
        invitation = invitations.invite(
            manager, "builders", self.users["outside"].username
        )
        self.assertFalse(
            self.group.memberships.filter(user=self.users["outside"]).exists()
        )
        wrong = self.post_json(
            f"/account/group-invitations/{invitation.pk}",
            {"decision": "accept"},
            **self.headers("member"),
        )
        self.assertEqual(wrong.status_code, 404)
        headers = self.headers("outside")
        inbox = self.client.get("/api/account/group-processes", **headers)
        self.assertEqual(inbox.status_code, 200, inbox.content)
        self.assertEqual(
            inbox.json()["items"][0]["process"]["status"], "pending"
        )
        for _ in range(2):
            response = self.post_json(
                f"/account/group-invitations/{invitation.pk}",
                {"decision": "accept"},
                **headers,
            )
            self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            self.group.memberships.filter(user=self.users["outside"]).count(),
            1,
        )
        self.assertEqual(
            GroupAuditEvent.objects.filter(
                action="member_joined", target=self.users["outside"]
            ).count(),
            1,
        )
        self.assertEqual(
            self.client.get("/api/account/groups", **headers).json()["total"],
            1,
        )

    def test_past_membership_does_not_reveal_current_private_group(self):
        PlayerGroup.objects.filter(pk=self.group.pk).update(
            access="private", join_mode="invite_only"
        )
        headers = self.headers("member")
        response = self.client.get("/api/account/groups", **headers)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            response.json()["items"][0]["group"]["slug"], "builders"
        )
        member = self.group.memberships.get(user=self.users["member"])
        member.status = "left"
        member.save()
        response = self.client.get(
            "/api/account/groups?history=true", **headers
        )
        self.assertEqual(response.status_code, 200, response.content)
        entry = response.json()["items"][0]
        self.assertIsNone(entry["group"])
        self.assertEqual(entry["membership"]["status"], "left")
        self.assertEqual(entry["membership"]["id"], member.pk)

    def test_validation_and_write_flag_preserve_reads(self):
        headers = self.headers("manager")
        for data in [
            {"version": 1, "created_by": 123},
            {
                "version": 1,
                "contacts": [
                    {
                        "type": "discord",
                        "label": "Unsafe",
                        "url": "javascript:alert(1)",
                    }
                ],
            },
            {"version": 1, "name": None},
        ]:
            self.assertEqual(
                self.patch_json(
                    "/groups/builders", data, **headers
                ).status_code,
                422,
            )
        flags = dict.fromkeys(HUB_FLAG_KEYS, True)
        flags["player_groups_write"] = False
        with patch("communities.access.flags_for", return_value=flags):
            response = self.patch_json(
                "/groups/builders",
                {"version": 1, "description": "blocked"},
                **headers,
            )
            self.assertEqual(
                response.json()["error_code"], "GROUP_WRITES_PAUSED"
            )
            self.assertEqual(
                self.client.get("/api/groups/builders", **headers).status_code,
                200,
            )
        with patch("communities.access.flags_for", return_value={}):
            self.assertEqual(self.client.get("/api/groups").status_code, 404)

    def test_join_request_review_role_offer_and_archive_end_to_end(self):
        self.group.join_mode = "approval"
        self.group.save()
        outside = self.headers("outside")
        manager = self.headers("manager")
        response = self.post_json(
            "/groups/builders/requests", {"answer": "Хочу строить"}, **outside
        )
        self.assertEqual(response.status_code, 200, response.content)
        request_id = response.json()["id"]
        review = self.post_json(
            f"/groups/builders/requests/{request_id}/decision",
            {"decision": "accept"},
            **manager,
        )
        self.assertEqual(review.status_code, 200, review.content)
        member = self.group.memberships.get(user=self.users["outside"])
        offer = self.post_json(
            "/groups/builders/leadership",
            {"membership_id": member.pk},
            **manager,
        )
        self.assertEqual(offer.status_code, 200, offer.content)
        self.assertEqual(member.role, "member")
        accept = self.post_json(
            f"/account/group-leadership/{offer.json()['id']}",
            {"decision": "accept"},
            **outside,
        )
        self.assertEqual(accept.status_code, 200, accept.content)
        archived = self.post_json(
            "/groups/builders/lifecycle",
            {"version": 1, "action": "archive"},
            **manager,
        )
        self.assertEqual(archived.status_code, 200, archived.content)
        self.assertEqual(self.client.get("/api/groups").json()["total"], 0)
