from django.db import migrations


def seed_homepage_feature(apps, schema_editor):
    FeatureDefinition = apps.get_model("featureflags", "FeatureDefinition")
    FeatureDefinition.objects.get_or_create(
        key="site_homepage_version",
        defaults={
            "description": "Homepage version rollout for /joutak",
            "kind": "variant",
            "default_value": "legacy",
            "active": True,
            "sticky_assignment": False,
        },
    )


def noop(apps, schema_editor):
    return None


class Migration(migrations.Migration):
    dependencies = [
        ("featureflags", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_homepage_feature, noop),
    ]
