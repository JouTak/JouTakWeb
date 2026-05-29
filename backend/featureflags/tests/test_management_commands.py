from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from featureflags.models import FeatureDefinition
from featureflags.registry import FEATURE_REGISTRY


class SyncFeatureRegistryCommandTests(TestCase):
    def test_sync_feature_registry_recreates_all_registered_features(
        self,
    ) -> None:
        FeatureDefinition.objects.all().delete()

        stdout = StringIO()
        call_command("sync_feature_registry", stdout=stdout)

        self.assertEqual(
            FeatureDefinition.objects.count(),
            len(FEATURE_REGISTRY),
        )
        self.assertIn("Feature registry sync complete", stdout.getvalue())
