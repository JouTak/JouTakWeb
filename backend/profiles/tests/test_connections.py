from unittest.mock import patch

from accounts.tests.base import APITestCase
from cities.models import City, CityMembership
from communities.models import Community, CommunityMembership
from core.models import UserProfile
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from featureflags.registry import HUB_FLAG_KEYS

from profiles.connections import search_players
from profiles.models import CommunityProfile, ProfileContact, ProfileFollow


class PlayerConnectionsTests(APITestCase):
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
        self.hidden = self.create_legacy_user(username="hidden")
        for user in (self.alice, self.bob):
            CommunityProfile.objects.create(
                user=user,
                visibility="public",
                display_name=user.username.title(),
            )
        CommunityProfile.objects.create(user=self.hidden, visibility="private")
        UserProfile.objects.update_or_create(
            user=self.bob, defaults={"minecraft_nick": "SecretNick"}
        )

    def headers(self, user):
        response = self.login(username=user.username)
        self.assertEqual(response.status_code, 200, response.content)
        return self.auth_headers(self.session_token(response))

    def test_search_filters_before_matching_and_pagination(self):
        response = self.client.get("/api/profiles/players")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 2)
        for q in ("SecretNick", self.bob.email, "hidden"):
            self.assertEqual(
                self.client.get("/api/profiles/players", {"q": q}).json()[
                    "total"
                ],
                0,
            )
        self.assertEqual(
            self.client.get("/api/profiles/players", {"q": "Bob"}).json()[
                "total"
            ],
            1,
        )
        self.assertEqual(
            self.client.get("/api/profiles/players", {"page": 0}).status_code,
            422,
        )
        self.assertEqual(
            self.client.get(
                "/api/profiles/players", {"following": True}
            ).status_code,
            401,
        )
        self.assertNotIn("email", str(response.json()))

    def test_shared_community_search_loses_access_on_suspension(self):
        CommunityProfile.objects.filter(user=self.bob).update(
            visibility="community"
        )
        community = Community.objects.create(slug="shared", name="Shared")
        for user in (self.alice, self.bob):
            CommunityMembership.objects.create(
                user=user, community=community, status="active"
            )
        headers = self.headers(self.alice)
        self.assertEqual(
            self.client.get(
                "/api/profiles/players", {"q": "SecretNick"}, **headers
            ).json()["total"],
            1,
        )
        CommunityMembership.objects.filter(user=self.alice).update(
            status="suspended"
        )
        self.assertEqual(
            self.client.get(
                "/api/profiles/players", {"q": "SecretNick"}, **headers
            ).json()["total"],
            0,
        )

    def test_follow_idempotency_privacy_and_unfollow_hidden_target(self):
        path = "/profiles/public/bob/follow"
        self.assertEqual(self.post_json(path).status_code, 401)
        headers = self.headers(self.alice)
        for _ in range(2):
            self.assertEqual(self.post_json(path, **headers).status_code, 200)
        self.assertEqual(ProfileFollow.objects.count(), 1)
        self.assertEqual(
            self.post_json(
                "/profiles/public/alice/follow", **headers
            ).status_code,
            422,
        )
        self.assertEqual(
            self.post_json(
                "/profiles/public/hidden/follow", **headers
            ).status_code,
            404,
        )
        own = self.client.get(
            "/api/profiles/players", {"following": True}, **headers
        ).json()
        self.assertEqual(own["items"][0]["username"], "bob")
        self.assertTrue(own["items"][0]["is_following"])
        hidden_list = self.client.get(
            "/api/profiles/public/alice/connections"
        ).json()
        self.assertFalse(hidden_list["is_visible"])
        CommunityProfile.objects.filter(user=self.alice).update(
            connections_visibility="public"
        )
        visible_list = self.client.get(
            "/api/profiles/public/alice/connections"
        ).json()
        self.assertEqual(visible_list["total"], 1)
        CommunityProfile.objects.filter(user=self.bob).update(
            visibility="private"
        )
        self.assertEqual(
            self.client.get(
                "/api/profiles/players", {"following": True}, **headers
            ).json()["total"],
            0,
        )
        self.assertEqual(self.delete_json(path, **headers).status_code, 200)
        self.assertEqual(self.delete_json(path, **headers).status_code, 200)
        self.assertFalse(ProfileFollow.objects.exists())

    def test_contacts_require_opt_in_and_reject_unsafe_values(self):
        headers = self.headers(self.alice)
        payload = {
            "version": 1,
            "contacts": [
                {
                    "type": "telegram",
                    "value": "@alice_test",
                    "visibility": "public",
                },
                {
                    "type": "discord",
                    "value": "alice.test",
                    "visibility": "private",
                },
            ],
        }
        response = self.patch_json("/profiles/me/contacts", payload, **headers)
        self.assertEqual(response.status_code, 200, response.content)
        public = self.client.get("/api/profiles/public/alice").json()[
            "contacts"
        ]
        self.assertEqual(len(public), 1)
        self.assertEqual(public[0]["url"], "https://t.me/alice_test")
        self.assertNotIn("visibility", public[0])
        for value in (
            "javascript:alert(1)",
            "https://t.me.evil.test/alice",
            "https://t.me/alice?token=x",
        ):
            payload["contacts"][0]["value"] = value
            self.assertEqual(
                self.patch_json(
                    "/profiles/me/contacts", payload, **headers
                ).status_code,
                422,
            )
        self.assertEqual(
            ProfileContact.objects.filter(user=self.alice).count(), 2
        )
        self.assertEqual(
            self.patch_json(
                "/profiles/me/contacts", {"version": 1, "contacts": []}
            ).status_code,
            401,
        )

    def test_follow_constraints_and_deletion(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProfileFollow.objects.create(user=self.alice, target=self.alice)
        ProfileFollow.objects.create(user=self.alice, target=self.bob)
        self.bob.delete()
        self.assertFalse(ProfileFollow.objects.exists())

    def test_private_followers_and_visibility_changes(self):
        ProfileFollow.objects.create(user=self.alice, target=self.bob)
        CommunityProfile.objects.filter(user=self.bob).update(
            connections_visibility="public"
        )
        path = "/api/profiles/public/bob/connections"
        self.assertEqual(
            self.client.get(path, {"direction": "followers"}).json()["total"],
            0,
        )
        CommunityProfile.objects.filter(user=self.alice).update(
            connections_visibility="public"
        )
        self.assertEqual(
            self.client.get(path, {"direction": "followers"}).json()["total"],
            1,
        )
        CommunityProfile.objects.filter(user=self.alice).update(
            visibility="private"
        )
        self.assertEqual(
            self.client.get(path, {"direction": "followers"}).json()["total"],
            0,
        )

    def test_pagination_has_bounded_queries(self):
        users = get_user_model().objects.bulk_create(
            [get_user_model()(username=f"search_{i:02d}") for i in range(26)]
        )
        CommunityProfile.objects.bulk_create(
            [
                CommunityProfile(user=user, visibility="public")
                for user in users
            ]
        )
        community = Community.objects.create(
            slug="directory", name="Directory"
        )
        CommunityMembership.objects.bulk_create(
            [
                CommunityMembership(
                    user=user, community=community, status="active"
                )
                for user in [*users, self.alice]
            ]
        )
        city = City.objects.create(
            community=community,
            slug="directory",
            name="Directory",
            short_description="Public directory city",
            status="active",
        )
        CityMembership.objects.bulk_create(
            [
                CityMembership(user=user, city=city, status="active")
                for user in users
            ]
        )
        with self.assertNumQueries(4):
            result = search_players(self.alice, "search_", 1, False)
        self.assertEqual(result.total, 26)
        self.assertEqual(len(result.items), 24)
        self.assertTrue(
            all(p.cities[0].slug == "directory" for p in result.items)
        )
        second = search_players(self.alice, "search_", 2, False)
        self.assertEqual(len(second.items), 2)
        self.assertFalse(
            {p.username for p in result.items}
            & {p.username for p in second.items}
        )

    def test_city_badges_obey_membership_and_community_visibility(self):
        public = Community.objects.create(slug="public", name="Public")
        internal = Community.objects.create(
            slug="internal", name="Internal", visibility="community"
        )
        for community in (public, internal):
            CommunityMembership.objects.create(
                user=self.bob, community=community, status="active"
            )
        CommunityMembership.objects.create(
            user=self.alice, community=public, status="active"
        )
        CommunityProfile.objects.filter(user=self.bob).update(
            memberships_visibility="public"
        )
        for slug, community, lifecycle, status, visibility in [
            ("open", public, "active", "active", "public"),
            ("private", public, "active", "active", "private"),
            ("draft", public, "draft", "active", "public"),
            ("archived", public, "archived", "active", "public"),
            ("left", public, "active", "left", "public"),
            ("internal", internal, "active", "active", "community"),
        ]:
            city = City.objects.create(
                slug=slug,
                name=slug,
                community=community,
                status=lifecycle,
                short_description="Visible city summary",
            )
            CityMembership.objects.create(
                user=self.bob,
                city=city,
                status=status,
                visibility=visibility,
                position="Архитектор",
            )
        response = self.client.get("/api/profiles/players", {"q": "bob"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["items"][0]["cities"],
            [
                {
                    "slug": "open",
                    "name": "open",
                    "role": "resident",
                    "position": "Архитектор",
                }
            ],
        )

        def city_slugs(viewer):
            return {
                c.slug
                for c in search_players(viewer, "bob", 1, False)
                .items[0]
                .cities
            }

        # Sharing another community does not unlock this city's relationship.
        self.assertEqual(city_slugs(self.alice), {"open"})
        member = CommunityMembership.objects.create(
            user=self.alice, community=internal, status="active"
        )
        self.assertEqual(city_slugs(self.alice), {"open", "internal"})
        CommunityProfile.objects.filter(user=self.bob).update(
            memberships_visibility="private"
        )
        self.assertEqual(city_slugs(self.alice), set())
        CommunityProfile.objects.filter(user=self.bob).update(
            memberships_visibility="public"
        )
        member.status = "suspended"
        member.save()
        self.assertEqual(city_slugs(self.alice), {"open"})
        CommunityMembership.objects.filter(
            user=self.bob, community=public
        ).update(status="suspended")
        self.assertEqual(city_slugs(self.alice), set())
        CommunityProfile.objects.filter(user=self.bob).update(
            memberships_visibility="private"
        )
        self.assertEqual(
            self.client.get("/api/profiles/players", {"q": "bob"}).json()[
                "items"
            ][0]["cities"],
            [],
        )

    def test_mutations_cannot_spoof_owner_and_obey_rollout_and_limit(self):
        headers = self.headers(self.alice)
        self.assertEqual(
            self.post_json(
                "/profiles/public/bob/follow", {"user": self.bob.pk}, **headers
            ).status_code,
            422,
        )
        with patch("profiles.social_api.ratelimit_method", return_value=True):
            response = self.post_json("/profiles/public/bob/follow", **headers)
            self.assertEqual(response.status_code, 429)
            self.assertEqual(
                response.json()["error_code"], "PROFILE_RATE_LIMITED"
            )
        with patch("communities.access.flags_for", return_value={}):
            self.assertEqual(
                self.client.get("/api/profiles/players").status_code, 404
            )
            self.assertEqual(
                self.post_json(
                    "/profiles/public/bob/follow", **headers
                ).status_code,
                404,
            )
        self.assertFalse(ProfileFollow.objects.exists())

    def test_partial_profile_save_preserves_connections_visibility(self):
        CommunityProfile.objects.filter(user=self.alice).update(
            connections_visibility="public"
        )
        headers = self.headers(self.alice)
        fields = (
            "version",
            "display_name",
            "bio",
            "avatar_url",
            "visibility",
            "minecraft_visibility",
            "social_visibility",
            "itmo_visibility",
            "memberships_visibility",
        )
        current = self.client.get("/api/profiles/me", **headers).json()
        response = self.patch_json(
            "/profiles/me",
            {key: current.get(key, "") for key in fields},
            **headers,
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["connections_visibility"], "public")

    def test_structured_private_vk_suppresses_legacy_public_vk_fallback(self):
        CommunityProfile.objects.filter(user=self.bob).update(
            social_visibility="public"
        )
        UserProfile.objects.filter(user=self.bob).update(
            vk_username="legacy_bob"
        )
        ProfileContact.objects.create(
            user=self.bob, type="vk", value="new_bob", visibility="private"
        )
        response = self.client.get("/api/profiles/public/bob")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("vk_url", response.json())
        self.assertEqual(response.json()["contacts"], [])
