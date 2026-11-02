from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class AdditiveMigrationTests(TransactionTestCase):
    def test_existing_private_identity_survives_upgrade(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        hub_apps = {"profiles", "communities", "cities"}
        before = [node for node in latest if node[0] not in hub_apps]
        executor.migrate(before + [(app, None) for app in hub_apps])
        try:
            state = executor.loader.project_state(before).apps
            user = state.get_model("auth", "User").objects.create(
                username="legacy_upgrade", email="private@example.local"
            )
            profile = state.get_model("core", "UserProfile").objects.create(
                user_id=user.pk,
                minecraft_nick="LegacyPlayer",
                minecraft_has_license=True,
                vk_username="legacy",
                is_itmo_student=True,
                itmo_isu="123456",
            )
            profile_id = profile.pk
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
        state = executor.loader.project_state(latest).apps
        upgraded = state.get_model("core", "UserProfile").objects.get(
            pk=profile_id
        )
        self.assertEqual(upgraded.minecraft_nick, "LegacyPlayer")
        self.assertEqual(upgraded.itmo_isu, "123456")
        self.assertTrue(upgraded.minecraft_has_license)
        self.assertEqual(
            state.get_model("profiles", "CommunityProfile").objects.count(), 0
        )

    def test_existing_community_profile_receives_default_server_date(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        before = (
            "profiles",
            "0003_communityprofile_connections_visibility_and_more",
        )
        executor.migrate([before])
        try:
            state = executor.loader.project_state([before]).apps
            user = state.get_model("auth", "User").objects.create(
                username="baseline"
            )
            profile = state.get_model(
                "profiles", "CommunityProfile"
            ).objects.create(
                user_id=user.pk,
                display_name="Имя",
                visibility="private",
                connections_visibility="private",
            )
            profile_id = profile.pk
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
        state = executor.loader.project_state(latest).apps
        upgraded = state.get_model("profiles", "CommunityProfile").objects.get(
            pk=profile_id
        )
        self.assertEqual(
            upgraded.minecraft_first_joined_at.date(), date(2026, 1, 1)
        )
        self.assertEqual(upgraded.display_name, "Имя")
        self.assertEqual(upgraded.visibility, "private")
        self.assertEqual(upgraded.connections_visibility, "private")
