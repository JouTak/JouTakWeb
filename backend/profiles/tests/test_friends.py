from unittest.mock import patch

from accounts.tests.base import APITestCase
from django.contrib.auth import get_user_model
from featureflags.registry import HUB_FLAG_KEYS

from profiles.connections import connections
from profiles.models import CommunityProfile, ProfileFollow


class FriendsTests(APITestCase):
    def setUp(self):
        super().setUp()
        flags = patch(
            "communities.access.flags_for",
            return_value=dict.fromkeys(HUB_FLAG_KEYS, True),
        )
        flags.start()
        self.addCleanup(flags.stop)
        self.alice = self.create_legacy_user(username="alice")
        self.bob = self.create_legacy_user(username="bob")
        for user in (self.alice, self.bob):
            CommunityProfile.objects.create(
                user=user, visibility="public", connections_visibility="public"
            )
        self.path = "/api/profiles/public/bob/connections"

    def listed(self, direction):
        response = self.client.get(self.path, {"direction": direction})
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_reply_follow_moves_follower_to_friends_and_unfollow_reverses(
        self,
    ):
        ProfileFollow.objects.create(user=self.alice, target=self.bob)
        self.assertEqual(self.listed("followers")["total"], 1)
        self.assertEqual(self.listed("friends")["total"], 0)
        headers = self.auth_headers(
            self.session_token(self.login(username="bob"))
        )
        self.assertEqual(
            self.post_json(
                "/profiles/public/alice/follow", **headers
            ).status_code,
            200,
        )
        self.assertEqual(self.listed("followers")["total"], 0)
        friends = self.listed("friends")
        self.assertEqual(friends["total"], 1)
        self.assertEqual(friends["items"][0]["username"], "alice")
        self.assertEqual(self.listed("following")["total"], 1)
        self.assertEqual(
            self.delete_json(
                "/profiles/public/alice/follow", **headers
            ).status_code,
            200,
        )
        self.assertEqual(self.listed("friends")["total"], 0)
        self.assertEqual(self.listed("followers")["total"], 1)

    def test_outgoing_only_is_not_a_friend_or_follower(self):
        ProfileFollow.objects.create(user=self.bob, target=self.alice)
        self.assertEqual(self.listed("following")["total"], 1)
        self.assertEqual(self.listed("friends")["total"], 0)
        self.assertEqual(self.listed("followers")["total"], 0)
        self.assertEqual(
            self.client.get(self.path, {"direction": "everyone"}).status_code,
            422,
        )

    def test_both_profiles_and_connection_visibility_filter_counts(self):
        ProfileFollow.objects.create(user=self.bob, target=self.alice)
        ProfileFollow.objects.create(user=self.alice, target=self.bob)
        self.assertEqual(self.listed("friends")["total"], 1)
        for visibility in ("private", "community"):
            CommunityProfile.objects.filter(user=self.alice).update(
                connections_visibility=visibility
            )
            self.assertEqual(self.listed("friends")["total"], 0)
        CommunityProfile.objects.filter(user=self.alice).update(
            connections_visibility="public", visibility="private"
        )
        self.assertEqual(self.listed("friends")["total"], 0)
        CommunityProfile.objects.filter(user=self.alice).update(
            visibility="public"
        )
        self.alice.is_active = False
        self.alice.save()
        self.assertEqual(self.listed("friends")["total"], 0)
        CommunityProfile.objects.filter(user=self.bob).update(
            connections_visibility="private"
        )
        result = self.listed("friends")
        self.assertFalse(result["is_visible"])
        self.assertEqual(result["items"], [])

    def test_friend_pagination_has_bounded_queries(self):
        users = get_user_model().objects.bulk_create(
            [get_user_model()(username=f"friend_{i:02d}") for i in range(26)]
        )
        CommunityProfile.objects.bulk_create(
            [
                CommunityProfile(
                    user=user,
                    visibility="public",
                    connections_visibility="public",
                )
                for user in users
            ]
        )
        ProfileFollow.objects.bulk_create(
            [
                ProfileFollow(user=source, target=target)
                for user in users
                for source, target in ((user, self.bob), (self.bob, user))
            ]
        )
        with self.assertNumQueries(5):
            result = connections("bob", None, "friends", 1)
        self.assertEqual(result.total, 26)
        self.assertEqual(len(result.items), 24)
        other = connections("bob", None, "friends", 2)
        self.assertEqual(len(other.items), 2)
        self.assertFalse(
            {p.username for p in result.items}
            & {p.username for p in other.items}
        )
