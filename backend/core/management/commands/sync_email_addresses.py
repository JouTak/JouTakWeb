from __future__ import annotations

from accounts.services.email_addresses import sync_user_email_address
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Backfill allauth EmailAddress rows from the user model email field "
        "for existing users."
    )

    def handle(self, *args, **options) -> None:
        created = 0
        updated_user_email = 0
        promoted_primary = 0

        users = User.objects.exclude(email__isnull=True).exclude(email="")
        for user in users.iterator():
            result = sync_user_email_address(user)
            created += int(result.created)
            updated_user_email += int(result.updated_user_email)
            promoted_primary += int(result.promoted_primary)

        self.stdout.write(
            self.style.SUCCESS(
                "sync_email_addresses completed: "
                f"created={created}, "
                f"updated_user_email={updated_user_email}, "
                f"promoted_primary={promoted_primary}"
            )
        )
