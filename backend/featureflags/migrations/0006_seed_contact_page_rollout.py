from __future__ import annotations

from django.db import migrations, transaction
from django.utils import timezone

FLAG_KEY = "site_contact_page_version"
FLAG_DESCRIPTION = "Switches the /contact page."
RULE_NAME = "Website design testers"
GROUP_SLUG = "website-design-testers"
PAGE = "contact"
HISTORY_REASON = "Add contact page design rollout"


def _snapshot_definition(
    historical_definition_model,
    definition,
    history_type="~",
):
    historical_definition_model.objects.create(
        id=definition.pk,
        key=definition.key,
        description=definition.description,
        kind=definition.kind,
        default_value=definition.default_value,
        active=definition.active,
        sticky_assignment=definition.sticky_assignment,
        created_at=definition.created_at,
        updated_at=definition.updated_at,
        history_date=timezone.now(),
        history_type=history_type,
        history_change_reason=HISTORY_REASON,
        history_user_id=None,
    )


def forward(apps, schema_editor):
    FeatureDefinition = apps.get_model("featureflags", "FeatureDefinition")
    HistoricalFeatureDefinition = apps.get_model(
        "featureflags", "HistoricalFeatureDefinition"
    )
    FeatureGroup = apps.get_model("featureflags", "FeatureGroup")
    FeatureRule = apps.get_model("featureflags", "FeatureRule")

    with transaction.atomic():
        definition = (
            FeatureDefinition.objects.select_for_update()
            .filter(key=FLAG_KEY)
            .first()
        )
        created = definition is None
        if created:
            definition = FeatureDefinition.objects.create(
                key=FLAG_KEY,
                description=FLAG_DESCRIPTION,
                kind="variant",
                default_value="legacy",
                active=True,
                sticky_assignment=False,
            )
        else:
            definition.description = FLAG_DESCRIPTION
            definition.kind = "variant"
            definition.default_value = "legacy"
            definition.active = True
            definition.sticky_assignment = False
            definition.save(
                update_fields=[
                    "description",
                    "kind",
                    "default_value",
                    "active",
                    "sticky_assignment",
                    "updated_at",
                ]
            )
        _snapshot_definition(
            HistoricalFeatureDefinition,
            definition,
            "+" if created else "~",
        )

        group, _ = FeatureGroup.objects.get_or_create(
            slug=GROUP_SLUG,
            defaults={
                "name": RULE_NAME,
                "description": (
                    "Authenticated testers allowed to see the v2 prototype."
                ),
            },
        )
        rule = (
            FeatureRule.objects.select_for_update()
            .filter(
                feature=definition,
                name=RULE_NAME,
                page=PAGE,
            )
            .first()
        )
        rule_values = {
            "priority": 10,
            "rule_type": "group",
            "value": "v2",
            "actor_ids": [],
            "group_ids": [group.pk],
            "percentage": None,
            "enabled": True,
        }
        if rule is None:
            FeatureRule.objects.create(
                feature=definition,
                name=RULE_NAME,
                page=PAGE,
                **rule_values,
            )
        else:
            for field, value in rule_values.items():
                setattr(rule, field, value)
            rule.save(update_fields=[*rule_values, "updated_at"])


def reverse(apps, schema_editor):
    FeatureDefinition = apps.get_model("featureflags", "FeatureDefinition")
    HistoricalFeatureDefinition = apps.get_model(
        "featureflags", "HistoricalFeatureDefinition"
    )

    with transaction.atomic():
        definition = (
            FeatureDefinition.objects.select_for_update()
            .filter(key=FLAG_KEY)
            .first()
        )
        if definition is None:
            return
        definition.rules.filter(
            name=RULE_NAME,
            page=PAGE,
        ).delete()
        _snapshot_definition(
            HistoricalFeatureDefinition,
            definition,
            "-",
        )
        definition.delete()


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("featureflags", "0005_reset_design_rollout"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
