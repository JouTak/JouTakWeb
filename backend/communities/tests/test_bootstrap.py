from importlib import import_module
from io import StringIO

from django.apps import apps
from django.core.management import call_command
from django.db import connection
from django.test import TestCase

from communities.models import Community


class ServerNamingTests(TestCase):
    def test_seed_is_idempotent_and_preserves_custom_content(self):
        for _ in range(2):
            call_command("seed_itmocraft_community", stdout=StringIO())
        community = Community.objects.get(slug="itmocraft")
        self.assertEqual(community.name, "JouTak SMP")
        self.assertEqual(Community.objects.count(), 1)
        community.description = "Existing content"
        community.save()
        call_command("seed_itmocraft_community", stdout=StringIO())
        community.refresh_from_db()
        self.assertEqual(community.description, "Existing content")

    def test_rename_preserves_slug_and_custom_names(self):
        server = Community.objects.create(
            slug="itmocraft", name="ItmoCraft", description="Existing"
        )
        migration = import_module(
            "communities.migrations.0003_joutak_smp_name"
        )
        migration.rename_server(apps, connection.schema_editor())
        server.refresh_from_db()
        self.assertEqual(server.name, "JouTak SMP")
        self.assertEqual(server.slug, "itmocraft")
        self.assertEqual(server.description, "Existing")
        server.name = "Custom name"
        server.save()
        migration.rename_server(apps, connection.schema_editor())
        server.refresh_from_db()
        self.assertEqual(server.name, "Custom name")
