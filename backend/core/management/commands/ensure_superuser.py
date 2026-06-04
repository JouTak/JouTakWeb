from __future__ import annotations

from accounts.services.email_addresses import sync_user_email_address
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction


class Command(BaseCommand):
    help = (
        "Create or update a superuser idempotently and keep its allauth "
        "EmailAddress row in sync."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", default="")
        parser.add_argument("--password", default="")

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        user_model = get_user_model()
        username = str(options["username"] or "").strip()
        email = str(options["email"] or "").strip()
        password = options["password"] or None

        if not username:
            raise CommandError("--username is required")

        username_field = user_model.USERNAME_FIELD
        email_field = None
        try:
            email_field = user_model._meta.get_field("email")
        except Exception:
            email_field = None

        lookup = {username_field: username}
        user = user_model._default_manager.filter(**lookup).first()
        created = False

        if not user:
            create_kwargs = {username_field: username, "password": password}
            if email_field is not None:
                create_kwargs["email"] = email
            try:
                user = user_model._default_manager.create_superuser(
                    **create_kwargs
                )
                created = True
            except IntegrityError:
                user = user_model._default_manager.get(**lookup)

        update_fields: list[str] = []
        if (
            email_field is not None
            and email
            and getattr(user, "email", "") != email
        ):
            user.email = email
            update_fields.append("email")
        if not getattr(user, "is_staff", False):
            user.is_staff = True
            update_fields.append("is_staff")
        if not getattr(user, "is_superuser", False):
            user.is_superuser = True
            update_fields.append("is_superuser")
        if password and not user.check_password(password):
            user.set_password(password)
            update_fields.append("password")

        if update_fields:
            user.save(update_fields=sorted(set(update_fields)))

        sync_user_email_address(user)

        if created:
            action = "Created"
        elif update_fields:
            action = "Updated"
        else:
            action = "Already up-to-date"

        self.stdout.write(
            self.style.SUCCESS(
                f"{action} superuser: {getattr(user, username_field)}"
            )
        )
