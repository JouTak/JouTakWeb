from __future__ import annotations

from django.db import migrations, transaction
from django.utils import timezone

FLAG_KEY = "site_contact_page_version"
FLAG_DESCRIPTION = "Switches the /contact page."
RULE_NAME = "Website design testers"
GROUP_SLUG = "website-design-testers"
PAGE = "contact"
HISTORY_REASON = "Add contact page design rollout"
PREVIOUS_DEFINITION_REASON = "Contact rollout pre-migration definition"
PREVIOUS_RULE_REASON = "Contact rollout pre-migration rule"
ROLLBACK_REASON = "Rollback contact page design rollout"


def _snapshot_definition(
    historical_definition_model,
    definition,
    history_type="~",
    history_reason=HISTORY_REASON,
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
        history_change_reason=history_reason,
        history_user_id=None,
    )


def _snapshot_rule(
    historical_rule_model,
    rule,
    history_type="~",
    history_reason=HISTORY_REASON,
):
    historical_rule_model.objects.create(
        id=rule.pk,
        feature_id=rule.feature_id,
        name=rule.name,
        priority=rule.priority,
        rule_type=rule.rule_type,
        value=rule.value,
        page=rule.page,
        actor_ids=rule.actor_ids,
        group_ids=rule.group_ids,
        percentage=rule.percentage,
        enabled=rule.enabled,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        history_date=timezone.now(),
        history_type=history_type,
        history_change_reason=history_reason,
        history_user_id=None,
    )


def forward(apps, schema_editor):
    FeatureDefinition = apps.get_model("featureflags", "FeatureDefinition")
    HistoricalFeatureDefinition = apps.get_model(
        "featureflags", "HistoricalFeatureDefinition"
    )
    HistoricalFeatureRule = apps.get_model(
        "featureflags", "HistoricalFeatureRule"
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
            _snapshot_definition(
                HistoricalFeatureDefinition,
                definition,
                history_reason=PREVIOUS_DEFINITION_REASON,
            )
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
            rule = FeatureRule.objects.create(
                feature=definition,
                name=RULE_NAME,
                page=PAGE,
                **rule_values,
            )
            rule_created = True
        else:
            _snapshot_rule(
                HistoricalFeatureRule,
                rule,
                history_reason=PREVIOUS_RULE_REASON,
            )
            for field, value in rule_values.items():
                setattr(rule, field, value)
            rule.save(update_fields=[*rule_values, "updated_at"])
            rule_created = False
        _snapshot_rule(
            HistoricalFeatureRule,
            rule,
            "+" if rule_created else "~",
        )


def reverse(apps, schema_editor):
    FeatureDefinition = apps.get_model("featureflags", "FeatureDefinition")
    HistoricalFeatureDefinition = apps.get_model(
        "featureflags", "HistoricalFeatureDefinition"
    )
    FeatureRule = apps.get_model("featureflags", "FeatureRule")
    HistoricalFeatureRule = apps.get_model(
        "featureflags", "HistoricalFeatureRule"
    )

    with transaction.atomic():
        definition = (
            FeatureDefinition.objects.select_for_update()
            .filter(key=FLAG_KEY)
            .first()
        )
        if definition is None:
            return

        migration_rule = (
            HistoricalFeatureRule.objects.filter(
                feature_id=definition.pk,
                history_change_reason=HISTORY_REASON,
                history_type__in=("+", "~"),
            )
            .order_by("-history_date", "-history_id")
            .first()
        )
        previous_rule = None
        if migration_rule is not None:
            previous_rule = (
                HistoricalFeatureRule.objects.filter(
                    id=migration_rule.id,
                    feature_id=definition.pk,
                    history_change_reason=PREVIOUS_RULE_REASON,
                )
                .order_by("-history_date", "-history_id")
                .first()
            )
            current_rule = FeatureRule.objects.filter(
                pk=migration_rule.id
            ).first()
            if previous_rule is not None and current_rule is not None:
                FeatureRule.objects.filter(pk=current_rule.pk).update(
                    feature_id=definition.pk,
                    name=previous_rule.name,
                    priority=previous_rule.priority,
                    rule_type=previous_rule.rule_type,
                    value=previous_rule.value,
                    page=previous_rule.page,
                    actor_ids=previous_rule.actor_ids,
                    group_ids=previous_rule.group_ids,
                    percentage=previous_rule.percentage,
                    enabled=previous_rule.enabled,
                    created_at=previous_rule.created_at,
                    updated_at=previous_rule.updated_at,
                )
                current_rule.refresh_from_db()
                _snapshot_rule(
                    HistoricalFeatureRule,
                    current_rule,
                    history_reason=ROLLBACK_REASON,
                )
            elif migration_rule.history_type == "+" and current_rule:
                _snapshot_rule(
                    HistoricalFeatureRule,
                    current_rule,
                    "-",
                    history_reason=ROLLBACK_REASON,
                )
                current_rule.delete()

        previous_definition = (
            HistoricalFeatureDefinition.objects.filter(
                id=definition.pk,
                history_change_reason=PREVIOUS_DEFINITION_REASON,
            )
            .order_by("-history_date", "-history_id")
            .first()
        )
        if previous_definition is not None:
            FeatureDefinition.objects.filter(pk=definition.pk).update(
                key=previous_definition.key,
                description=previous_definition.description,
                kind=previous_definition.kind,
                default_value=previous_definition.default_value,
                active=previous_definition.active,
                sticky_assignment=previous_definition.sticky_assignment,
                created_at=previous_definition.created_at,
                updated_at=previous_definition.updated_at,
            )
            definition.refresh_from_db()
            _snapshot_definition(
                HistoricalFeatureDefinition,
                definition,
                history_reason=ROLLBACK_REASON,
            )
        else:
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
