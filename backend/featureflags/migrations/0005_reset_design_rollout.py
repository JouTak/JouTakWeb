from __future__ import annotations

from django.db import migrations, transaction
from django.utils import timezone

CANONICAL_FLAGS = {
    "site_itmocraft_page_version": (
        "Switches the canonical / ITMOcraft page.",
        "itmocraft",
    ),
    "site_joutak_page_version": (
        "Switches the /joutak product page.",
        "joutak",
    ),
    "site_minigames_page_version": (
        "Switches the /minigames product page.",
        "minigames",
    ),
    "site_header_version": ("Switches the shared site header.", ""),
    "site_footer_version": ("Switches the shared site footer.", ""),
}

RETIRED_KEYS = {
    *CANONICAL_FLAGS,
    "site_homepage_version",
    "site_homepage_page_version",
    "site_header_v2",
    "site_footer_v2",
    "itmocraft_new_header",
    "joutak_projects_section",
    "joutak_hero_section",
    "joutak_events_section",
    "joutak_faq_section",
    "joutak_gallery_section",
    "joutak_new_hero_section",
    "joutak_new_gallery_section",
    "minigames_new_hero_section",
    "minigames_new_projects_section",
    "minigames_new_gallery_section",
    "minigames_new_events_section",
    "itmocraft_new_hero_section",
    "itmocraft_new_projects_section",
    "itmocraft_new_gallery_section",
    "itmocraft_new_events_section",
    "itmocraft_new_faq_section",
}


def _snapshot(HistoricalFeatureDefinition, definition, history_type="~"):
    HistoricalFeatureDefinition.objects.create(
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
        history_change_reason="PR #129 design rollout migration",
        history_user_id=None,
    )


def _archive_key(definition, *, prefix="p129"):
    active = "1" if definition.active else "0"
    return f"{prefix}_a{active}_{definition.pk}__{definition.key}"


def forward(apps, schema_editor):
    FeatureDefinition = apps.get_model(
        "featureflags", "FeatureDefinition"
    )
    HistoricalFeatureDefinition = apps.get_model(
        "featureflags", "HistoricalFeatureDefinition"
    )
    FeatureGroup = apps.get_model("featureflags", "FeatureGroup")
    FeatureRule = apps.get_model("featureflags", "FeatureRule")

    with transaction.atomic():
        definitions = list(
            FeatureDefinition.objects.select_for_update().filter(
                key__in=RETIRED_KEYS
            )
        )
        for definition in definitions:
            definition.key = _archive_key(definition)
            definition.active = False
            definition.save(update_fields=["key", "active", "updated_at"])
            _snapshot(HistoricalFeatureDefinition, definition)

        group, _ = FeatureGroup.objects.get_or_create(
            slug="website-design-testers",
            defaults={
                "name": "Website design testers",
                "description": (
                    "Authenticated testers allowed to see the v2 prototype."
                ),
            },
        )

        for key, (description, page) in CANONICAL_FLAGS.items():
            definition = FeatureDefinition.objects.create(
                key=key,
                description=description,
                kind="variant",
                default_value="legacy",
                active=True,
                sticky_assignment=False,
            )
            _snapshot(HistoricalFeatureDefinition, definition, "+")
            FeatureRule.objects.create(
                feature=definition,
                name="Website design testers",
                priority=10,
                rule_type="group",
                value="v2",
                page=page,
                actor_ids=[],
                group_ids=[group.pk],
                percentage=None,
                enabled=True,
            )


def reverse(apps, schema_editor):
    FeatureDefinition = apps.get_model(
        "featureflags", "FeatureDefinition"
    )
    HistoricalFeatureDefinition = apps.get_model(
        "featureflags", "HistoricalFeatureDefinition"
    )

    with transaction.atomic():
        current = list(
            FeatureDefinition.objects.select_for_update().filter(
                key__in=CANONICAL_FLAGS
            )
        )
        for definition in current:
            definition.key = _archive_key(
                definition,
                prefix="rollback_p129",
            )
            definition.active = False
            definition.save(update_fields=["key", "active", "updated_at"])
            _snapshot(HistoricalFeatureDefinition, definition)

        archived = list(
            FeatureDefinition.objects.select_for_update().filter(
                key__startswith="p129_a"
            )
        )
        for definition in archived:
            metadata, original_key = definition.key.split("__", 1)
            definition.key = original_key
            definition.active = metadata.startswith("p129_a1_")
            definition.save(update_fields=["key", "active", "updated_at"])
            _snapshot(HistoricalFeatureDefinition, definition)


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        (
            "featureflags",
            "0004_alter_experimentassignment_options_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
