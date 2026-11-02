from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase


class DemoGuardTests(TestCase):
    def test_demo_seed_refuses_other_databases(self):
        with self.assertRaises(CommandError):
            call_command("seed_player_groups_demo")


class UpgradeTests(TransactionTestCase):
    def test_existing_server_city_and_private_identity_survive(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        before = [
            (a, m)
            for a, m in latest
            if a not in {"playergroups", "communities"}
        ] + [("communities", "0001_initial")]
        executor.migrate(before + [("playergroups", None)])
        try:
            apps = executor.loader.project_state(before).apps
            user = apps.get_model("auth", "User").objects.create(
                username="upgrade_player", email="private@example.local"
            )
            profile = apps.get_model("core", "UserProfile").objects.create(
                user_id=user.pk,
                minecraft_nick="PlayerCraft",
                itmo_isu="123456",
                is_itmo_student=True,
            )
            community = apps.get_model(
                "communities", "Community"
            ).objects.create(
                slug="existing", name="Existing", visibility="private"
            )
            server_member = apps.get_model(
                "communities", "CommunityMembership"
            ).objects.create(
                user_id=user.pk,
                community_id=community.pk,
                status="suspended",
                role="moderator",
            )
            city = apps.get_model("cities", "City").objects.create(
                slug="existing-town",
                name="Город",
                short_description="Сохранить",
                community_id=community.pk,
            )
            city_member = apps.get_model(
                "cities", "CityMembership"
            ).objects.create(
                user_id=user.pk,
                city_id=city.pk,
                status="active",
                role="manager",
            )
            ids = (
                profile.pk,
                community.pk,
                server_member.pk,
                city.pk,
                city_member.pk,
            )
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
        apps = executor.loader.project_state(latest).apps
        self.assertEqual(
            apps.get_model("core", "UserProfile")
            .objects.get(pk=ids[0])
            .itmo_isu,
            "123456",
        )
        self.assertEqual(
            apps.get_model("communities", "Community")
            .objects.get(pk=ids[1])
            .visibility,
            "private",
        )
        self.assertEqual(
            apps.get_model("communities", "CommunityMembership")
            .objects.get(pk=ids[2])
            .status,
            "suspended",
        )
        self.assertEqual(
            apps.get_model("cities", "City")
            .objects.get(pk=ids[3])
            .short_description,
            "Сохранить",
        )
        self.assertEqual(
            apps.get_model("cities", "CityMembership")
            .objects.get(pk=ids[4])
            .role,
            "manager",
        )
        self.assertEqual(
            apps.get_model("playergroups", "GroupMembership").objects.count(),
            0,
        )
