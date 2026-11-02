from accounts.tests.base import APITestCase
from communities.models import Community, CommunityMembership
from core.models import UserProfile
from playergroups.models import GroupMembership, PlayerGroup

from profiles.models import CommunityProfile, ProfileContact, ProfileFollow
from profiles.tests.test_editing import ProfileEditingData


class ProfileProjectionTests(ProfileEditingData, APITestCase):
    def test_guest_preview_matches_all_guest_projections(
        self,
    ):
        self.profile.connections_visibility = "public"
        self.profile.memberships_visibility = "public"
        self.profile.save()
        UserProfile.objects.update_or_create(
            user=self.owner,
            defaults={"minecraft_nick": "PrivateNick", "itmo_isu": "123456"},
        )
        ProfileContact.objects.create(
            user=self.owner,
            type="telegram",
            value="private_contact",
            visibility="private",
        )
        guest = self.client.get("/api/profiles/public/editor").json()
        result = self.client.get("/api/profiles/me/preview", **self.headers)
        self.assertEqual(result.status_code, 200, result.content)
        self.assertEqual(result.json()["profile"], guest)
        self.assertNotIn("PrivateNick", str(result.json()))
        self.assertNotIn("private_contact", str(result.json()))
        self.assertNotIn("123456", str(result.json()))
        self.assertFalse(result.json()["profile"]["is_self"])
        self.assertEqual(result["Cache-Control"], "private, no-store")
        for kind in ("friends", "followers"):
            self.assertEqual(
                self.client.get(
                    f"/api/profiles/me/preview/connections?direction={kind}",
                    **self.headers,
                ).json(),
                self.client.get(
                    f"/api/profiles/public/editor/connections?direction={kind}"
                ).json(),
            )
        group = PlayerGroup.objects.create(
            slug="quiet-club",
            name="Quiet",
            short_description="Not discoverable",
            status="active",
            access="unlisted",
        )
        GroupMembership.objects.create(
            group=group, user=self.owner, visibility="public"
        )
        self.assertEqual(
            self.client.get(
                "/api/profiles/me/preview/groups", **self.headers
            ).json()["total"],
            0,
        )
        self.assertEqual(
            self.client.get("/api/profiles/public/editor/groups").json()[
                "total"
            ],
            0,
        )
        for mode in ("private", "community"):
            CommunityProfile.objects.filter(user=self.owner).update(
                visibility=mode
            )
            self.assertFalse(
                self.client.get("/api/profiles/me/preview", **self.headers)
                .json()
                .get("profile")
            )
            self.assertEqual(
                self.client.get(
                    "/api/profiles/me/preview/connections", **self.headers
                ).status_code,
                404,
            )
            self.assertEqual(
                self.client.get(
                    "/api/profiles/me/preview/groups", **self.headers
                ).status_code,
                404,
            )
        self.assertEqual(
            self.client.get("/api/profiles/me/preview").status_code, 401
        )

    def test_own_private_contact_and_itmo_are_visible_without_guest_bypass(
        self,
    ):
        self.profile.itmo_visibility = "private"
        self.profile.save()
        UserProfile.objects.update_or_create(
            user=self.owner, defaults={"is_itmo_student": False}
        )
        own = self.client.get(
            "/api/profiles/public/editor", **self.headers
        ).json()
        self.assertIs(own["itmo_student"], False)
        self.assertNotIn(
            "itmo_student",
            self.client.get("/api/profiles/public/editor").json(),
        )

    def test_own_hidden_follow_can_be_removed_by_scoped_id(self):
        hidden = self.create_legacy_user(username="hidden_target")
        CommunityProfile.objects.create(
            user=hidden, visibility="private", display_name="Do not reveal"
        )
        relation = ProfileFollow.objects.create(user=self.owner, target=hidden)
        foreign = ProfileFollow.objects.create(user=hidden, target=self.owner)
        response = self.client.get(
            "/api/profiles/me/following", **self.headers
        )
        self.assertEqual(
            response.json()["items"], [{"id": relation.pk, "profile": None}]
        )
        self.assertNotIn("hidden_target", str(response.json()))
        self.assertEqual(
            self.delete_json(
                f"/profiles/me/following/{foreign.pk}", **self.headers
            ).status_code,
            404,
        )
        self.assertTrue(ProfileFollow.objects.filter(pk=foreign.pk).exists())
        self.assertEqual(
            self.delete_json(
                f"/profiles/me/following/{relation.pk}", **self.headers
            ).status_code,
            200,
        )
        self.assertFalse(ProfileFollow.objects.filter(pk=relation.pk).exists())

    def test_common_club_never_reveals_community_contact(self):
        viewer = self.create_legacy_user(username="club_viewer")
        CommunityProfile.objects.create(user=viewer, visibility="public")
        ProfileContact.objects.create(
            user=self.owner,
            type="telegram",
            value="server_contact",
            visibility="community",
        )
        group = PlayerGroup.objects.create(
            slug="club", name="Club", short_description="Club", status="active"
        )
        for user in (viewer, self.owner):
            GroupMembership.objects.create(group=group, user=user)
        login = self.login(username=viewer.username)
        headers = self.auth_headers(self.session_token(login))
        self.assertEqual(
            self.client.get("/api/profiles/public/editor", **headers).json()[
                "contacts"
            ],
            [],
        )
        community = Community.objects.create(slug="server", name="Server")
        for user in (viewer, self.owner):
            CommunityMembership.objects.create(
                user=user, community=community, status="active"
            )
        self.assertEqual(
            len(
                self.client.get(
                    "/api/profiles/public/editor", **headers
                ).json()["contacts"]
            ),
            1,
        )
        member = CommunityMembership.objects.get(
            user=viewer, community=community
        )
        member.status = "suspended"
        member.save()
        self.assertEqual(
            self.client.get("/api/profiles/public/editor", **headers).json()[
                "contacts"
            ],
            [],
        )
