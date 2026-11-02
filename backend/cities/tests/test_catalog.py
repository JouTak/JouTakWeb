from core.models import UserProfile
from django.test import TestCase
from profiles.models import CommunityProfile

from cities.catalog import catalog_cards
from cities.models import City, CityMembership
from cities.queries import public_cities
from cities.tests.test_hub import HubData


class CatalogTests(HubData, TestCase):
    def setUp(self):
        self.manager = self.users["manager"]
        self.profile = CommunityProfile.objects.create(
            user=self.manager,
            display_name="Private Real Name",
            visibility="public",
            memberships_visibility="public",
            minecraft_visibility="public",
        )
        UserProfile.objects.create(
            user=self.manager, minecraft_nick="MayorCraft"
        )
        self.city.memberships.filter(user=self.manager).update(
            visibility="public", position="Мэр"
        )

    def cards(self, viewer=None, *, map_enabled=True):
        return catalog_cards(
            public_cities(viewer),
            viewer,
            {"cities_map_integration": map_enabled},
        )

    def test_guest_gets_public_leader_count_and_canonical_map(self):
        card = self.cards()[0]
        self.assertEqual(
            card.leader.model_dump(),
            {
                "username": "manager",
                "minecraft_nick": "MayorCraft",
                "position": "Мэр",
            },
        )
        self.assertEqual(card.member_count, 3)
        self.assertEqual(
            card.map_url,
            "https://map.joutak.ru/#joutak:1240:0:-438:1500:0:0:0:1:flat",
        )
        self.assertNotIn("Private Real Name", card.model_dump_json())
        self.assertIsNone(self.cards(map_enabled=False)[0].map_url)
        City.objects.filter(pk=self.city.pk).update(x=None, z=None)
        self.assertIsNone(self.cards()[0].map_url)

    def test_identity_and_membership_privacy_are_enforced(self):
        for field in ("visibility", "memberships_visibility"):
            for audience in ("private", "community"):
                with self.subTest(field=field, audience=audience):
                    setattr(self.profile, field, audience)
                    self.profile.save()
                    self.assertIsNone(self.cards()[0].leader)
                    shared_leader = self.cards(self.users["resident"])[
                        0
                    ].leader
                    self.assertEqual(
                        shared_leader is not None, audience == "community"
                    )
                    self.assertIsNotNone(self.cards(self.manager)[0].leader)
            setattr(self.profile, field, "public")
            self.profile.save()
        self.profile.minecraft_visibility = "private"
        self.profile.save()
        self.assertIsNone(self.cards()[0].leader.minecraft_nick)
        self.city.memberships.filter(user=self.manager).update(
            visibility="private"
        )
        self.assertIsNone(self.cards()[0].leader)
        self.assertIsNone(self.cards(self.users["resident"])[0].leader)
        self.assertIsNotNone(self.cards(self.manager)[0].leader)

    def test_inactive_manager_is_not_presented(self):
        self.manager.community_memberships.update(status="left")
        self.assertIsNone(self.cards()[0].leader)
        self.manager.community_memberships.update(status="active")
        self.manager.is_active = False
        self.manager.save()
        self.assertIsNone(self.cards()[0].leader)
        self.manager.is_active = True
        self.manager.save()
        self.city.memberships.filter(user=self.manager).update(
            status="removed"
        )
        self.assertIsNone(self.cards()[0].leader)

    def test_mayor_position_selects_between_visible_managers_only(self):
        other = self.users["representative"]
        CommunityProfile.objects.create(
            user=other, visibility="public", memberships_visibility="public"
        )
        self.city.memberships.filter(user=self.manager).update(
            position="Архитектор"
        )
        self.city.memberships.filter(user=other).update(
            position="Мэр", visibility="public"
        )
        self.assertEqual(self.cards()[0].leader.username, "manager")
        self.city.memberships.filter(user=other).update(role="manager")
        self.assertEqual(self.cards()[0].leader.username, "representative")

    def test_catalog_query_count_does_not_grow_per_city(self):
        with self.assertNumQueries(3):
            self.assertEqual(len(self.cards()), 1)
        for index in range(5):
            city = City.objects.create(
                community=self.community,
                slug=f"city-{index}",
                name=f"City {index}",
                short_description="Test",
                status="active",
            )
            CityMembership.objects.create(
                city=city,
                user=self.manager,
                status="active",
                role="manager",
                visibility="public",
            )
        with self.assertNumQueries(3):
            self.assertEqual(len(self.cards()), 6)
