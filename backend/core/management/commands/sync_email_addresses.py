from __future__ import annotations

from allauth.account.models import EmailAddress
from allauth.account.utils import user_email
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
            current_email = user_email(user)
            if not current_email:
                continue

            primary = EmailAddress.objects.get_primary(user)
            if primary:
                if primary.email != current_email:
                    user_email(user, primary.email, commit=True)
                    updated_user_email += 1
                continue

            try:
                email_address = EmailAddress.objects.get_for_user(
                    user, current_email
                )
            except EmailAddress.DoesNotExist:
                email_address = EmailAddress.objects.add_email(
                    request=None,
                    user=user,
                    email=current_email,
                    confirm=False,
                )
                created += 1

            if email_address.set_as_primary(conditional=True):
                promoted_primary += 1

        self.stdout.write(
            self.style.SUCCESS(
                "sync_email_addresses completed: "
                f"created={created}, "
                f"updated_user_email={updated_user_email}, "
                f"promoted_primary={promoted_primary}"
            )
        )
