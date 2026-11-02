from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ProfileUpgradeTests(TransactionTestCase):
    def test_version_upgrade_preserves_audiences_contacts_and_baseline(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        before = [(a, n) for a, n in latest if a != "profiles"] + [
            ("profiles", "0004_communityprofile_minecraft_first_joined_at")
        ]
        executor.migrate(before)
        try:
            apps = executor.loader.project_state(before).apps
            user = apps.get_model("auth", "User").objects.create(
                username="existing_profile"
            )
            profile = apps.get_model(
                "profiles", "CommunityProfile"
            ).objects.create(
                user_id=user.pk,
                visibility="community",
                bio="Сохранить",
                social_visibility="public",
            )
            contact = apps.get_model(
                "profiles", "ProfileContact"
            ).objects.create(
                user_id=user.pk,
                type="vk",
                value="private_vk",
                visibility="private",
            )
            original = (
                profile.pk,
                profile.minecraft_first_joined_at,
                contact.pk,
            )
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
        apps = executor.loader.project_state(latest).apps
        restored = apps.get_model("profiles", "CommunityProfile").objects.get(
            pk=original[0]
        )
        self.assertEqual(restored.visibility, "community")
        self.assertEqual(restored.bio, "Сохранить")
        self.assertEqual(restored.minecraft_first_joined_at, original[1])
        self.assertTrue(restored.legacy_vk_enabled)
        self.assertEqual((restored.version, restored.contacts_version), (1, 1))
        self.assertEqual(
            apps.get_model("profiles", "ProfileContact")
            .objects.get(pk=original[2])
            .visibility,
            "private",
        )
