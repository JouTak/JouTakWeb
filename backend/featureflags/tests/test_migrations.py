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
    migrate_latest = ("featureflags", "0006_seed_contact_page_rollout")

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
        self._migrate(self.migrate_latest)
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


class ContactPageRolloutMigrationTests(TransactionTestCase):
    migrate_from = ("featureflags", "0005_reset_design_rollout")
    migrate_to = ("featureflags", "0006_seed_contact_page_rollout")

    def _migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        return executor.loader.project_state([target]).apps

    def setUp(self):
        old_apps = self._migrate(self.migrate_from)
        User = old_apps.get_model("auth", "User")
        FeatureDefinition = old_apps.get_model(
            "featureflags", "FeatureDefinition"
        )
        FeatureGroup = old_apps.get_model("featureflags", "FeatureGroup")
        FeatureRule = old_apps.get_model("featureflags", "FeatureRule")

        self.member = User.objects.create(username="contact-rollout-tester")
        self.member_pk = self.member.pk
        group, _ = FeatureGroup.objects.get_or_create(
            slug="website-design-testers",
            defaults={"name": "Website design testers"},
        )
        group.members.add(self.member)
        self.group_pk = group.pk
        unrelated_definition, _ = FeatureDefinition.objects.get_or_create(
            key="site_joutak_page_version",
            defaults={
                "description": "Switches the /joutak product page.",
                "kind": "variant",
                "default_value": "legacy",
                "active": True,
                "sticky_assignment": False,
            },
        )
        unrelated_rule, _ = FeatureRule.objects.update_or_create(
            feature=unrelated_definition,
            name="Website design testers",
            page="joutak",
            defaults={
                "priority": 10,
                "rule_type": "group",
                "value": "v2",
                "actor_ids": [],
                "group_ids": [group.pk],
                "percentage": None,
                "enabled": True,
            },
        )
        self.unrelated_rule_pk = unrelated_rule.pk

    def tearDown(self):
        self._migrate(self.migrate_to)
        super().tearDown()

    def test_forward_seeds_closed_contact_rollout_and_preserves_group(self):
        apps = self._migrate(self.migrate_to)
        FeatureDefinition = apps.get_model("featureflags", "FeatureDefinition")
        FeatureGroup = apps.get_model("featureflags", "FeatureGroup")
        FeatureRule = apps.get_model("featureflags", "FeatureRule")
        HistoricalFeatureDefinition = apps.get_model(
            "featureflags", "HistoricalFeatureDefinition"
        )

        definition = FeatureDefinition.objects.get(
            key="site_contact_page_version"
        )
        self.assertEqual(definition.kind, "variant")
        self.assertEqual(definition.default_value, "legacy")
        self.assertTrue(definition.active)
        self.assertFalse(definition.sticky_assignment)

        rule = definition.rules.get(
            name="Website design testers",
            page="contact",
        )
        self.assertEqual(rule.priority, 10)
        self.assertEqual(rule.rule_type, "group")
        self.assertEqual(rule.value, "v2")
        self.assertEqual(rule.actor_ids, [])
        self.assertEqual(rule.group_ids, [self.group_pk])
        self.assertIsNone(rule.percentage)
        self.assertTrue(rule.enabled)

        group = FeatureGroup.objects.get(pk=self.group_pk)
        self.assertTrue(group.members.filter(pk=self.member_pk).exists())
        self.assertTrue(
            FeatureRule.objects.filter(pk=self.unrelated_rule_pk).exists()
        )
        self.assertTrue(
            HistoricalFeatureDefinition.objects.filter(
                id=definition.pk,
                key="site_contact_page_version",
                history_type="+",
                history_change_reason="Add contact page design rollout",
            ).exists()
        )

    def test_reverse_removes_only_contact_rollout(self):
        self._migrate(self.migrate_to)
        apps = self._migrate(self.migrate_from)
        FeatureDefinition = apps.get_model("featureflags", "FeatureDefinition")
        FeatureGroup = apps.get_model("featureflags", "FeatureGroup")
        FeatureRule = apps.get_model("featureflags", "FeatureRule")
        HistoricalFeatureDefinition = apps.get_model(
            "featureflags", "HistoricalFeatureDefinition"
        )

        self.assertFalse(
            FeatureDefinition.objects.filter(
                key="site_contact_page_version"
            ).exists()
        )
        group = FeatureGroup.objects.get(pk=self.group_pk)
        self.assertTrue(group.members.filter(pk=self.member_pk).exists())
        self.assertTrue(
            FeatureRule.objects.filter(pk=self.unrelated_rule_pk).exists()
        )
        self.assertTrue(
            HistoricalFeatureDefinition.objects.filter(
                key="site_contact_page_version",
                history_type="-",
                history_change_reason="Add contact page design rollout",
            ).exists()
        )
