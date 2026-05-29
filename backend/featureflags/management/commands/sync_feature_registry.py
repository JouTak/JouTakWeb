"""
Management command to synchronize the feature flag registry with the database.

Creates or updates FeatureDefinition records from the declarative
FEATURE_REGISTRY. Safe to run multiple times (idempotent). Intended to
be called during deployment (docker-entrypoint.sh) and development.

Usage:
    python manage.py sync_feature_registry
    python manage.py sync_feature_registry --dry-run
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from featureflags.models import FeatureDefinition, FeatureKind
from featureflags.registry import FEATURE_REGISTRY, get_default_value


class Command(BaseCommand):
    help = (
        "Synchronize feature flag definitions from the registry "
        "to the database. Creates new flags and updates metadata "
        "for existing ones (does not overwrite admin-configured "
        "default_value or active status)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes.",
        )
        parser.add_argument(
            "--force-defaults",
            action="store_true",
            help=(
                "Also update default_value from registry (overwrites "
                "admin changes). Use with caution."
            ),
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force_defaults = options["force_defaults"]
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for key, spec in FEATURE_REGISTRY.items():
            kind = (
                FeatureKind.VARIANT
                if spec["kind"] == "variant"
                else FeatureKind.BOOLEAN
            )
            default_value = str(get_default_value(key))
            sticky = spec.get("sticky", False)
            description = spec.get("description", "")

            existing = FeatureDefinition.objects.filter(key=key).first()

            if existing is None:
                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [CREATE] {key} "
                            f"(kind={kind}, default={default_value})"
                        )
                    )
                else:
                    FeatureDefinition.objects.create(
                        key=key,
                        kind=kind,
                        default_value=default_value,
                        sticky_assignment=sticky,
                        description=description,
                        active=True,
                    )
                    self.stdout.write(self.style.SUCCESS(f"  Created: {key}"))
                created_count += 1
            else:
                # Update metadata fields that won't break admin config
                updates = {}
                if existing.kind != kind:
                    updates["kind"] = kind
                if existing.sticky_assignment != sticky:
                    updates["sticky_assignment"] = sticky
                if existing.description != description:
                    updates["description"] = description
                if force_defaults and str(existing.default_value) != str(
                    default_value
                ):
                    updates["default_value"] = default_value

                if updates:
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  [UPDATE] {key}: "
                                f"{', '.join(updates.keys())}"
                            )
                        )
                    else:
                        for field, value in updates.items():
                            setattr(existing, field, value)
                        existing.save(update_fields=list(updates.keys()))
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Updated: {key} "
                                f"({', '.join(updates.keys())})"
                            )
                        )
                    updated_count += 1
                else:
                    skipped_count += 1

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(
            f"\n{prefix}Feature registry sync complete: "
            f"{created_count} created, {updated_count} updated, "
            f"{skipped_count} unchanged."
        )
