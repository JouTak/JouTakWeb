from __future__ import annotations

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class DesignRolloutMigrationTests(TransactionTestCase):
    migrate_from = (
        "featureflags",
        "0004_alter_experimentassignment_options_and_more",
    )
    migrate_to = ("featureflags", "0005_reset_design_rollout")

    def _migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        return executor.loader.project_state([target]).apps

    def setUp(self):
        old_apps = self._migrate(self.migrate_from)
        FeatureDefinition = old_apps.get_model(
            "featureflags", "FeatureDefinition"
        )
        FeatureRule = old_apps.get_model("featureflags", "FeatureRule")

        self.old_definition = FeatureDefinition.objects.create(
            key="site_header_version",
            description="Existing preview",
            kind="variant",
            default_value="v2",
            active=False,
            sticky_assignment=True,
        )
        self.old_pk = self.old_definition.pk
        FeatureRule.objects.create(
            feature=self.old_definition,
            name="Existing rule",
            priority=20,
            rule_type="everyone",
            value="v2",
            enabled=True,
        )

    def tearDown(self):
        self._migrate(self.migrate_to)
        super().tearDown()

    def test_forward_preserves_children_and_seeds_closed_rollout(self):
        apps = self._migrate(self.migrate_to)
        FeatureDefinition = apps.get_model("featureflags", "FeatureDefinition")
        FeatureGroup = apps.get_model("featureflags", "FeatureGroup")

        design_keys = {
            "site_itmocraft_page_version",
            "site_joutak_page_version",
            "site_minigames_page_version",
            "site_header_version",
            "site_footer_version",
        }
        active = FeatureDefinition.objects.filter(
            active=True,
            key__in=design_keys,
        )
        self.assertEqual(
            set(active.values_list("key", flat=True)),
            design_keys,
        )
        self.assertFalse(
            active.exclude(
                kind="variant",
                default_value="legacy",
                sticky_assignment=False,
            ).exists()
        )

        archived = FeatureDefinition.objects.get(pk=self.old_pk)
        self.assertTrue(archived.key.startswith("p129_a0_"))
        self.assertFalse(archived.active)
        self.assertEqual(archived.rules.count(), 1)

        group = FeatureGroup.objects.get(slug="website-design-testers")
        self.assertEqual(group.members.count(), 0)
        self.assertEqual(
            sum(definition.rules.count() for definition in active),
            5,
        )

    def test_reverse_restores_original_key_and_active_state(self):
        self._migrate(self.migrate_to)
        apps = self._migrate(self.migrate_from)
        FeatureDefinition = apps.get_model("featureflags", "FeatureDefinition")

        restored = FeatureDefinition.objects.get(pk=self.old_pk)
        self.assertEqual(restored.key, "site_header_version")
        self.assertFalse(restored.active)
        self.assertTrue(restored.sticky_assignment)
        self.assertEqual(restored.rules.count(), 1)
