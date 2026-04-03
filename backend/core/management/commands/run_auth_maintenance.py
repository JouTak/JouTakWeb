from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Run auth/session maintenance pipeline: clearsessions, "
        "flushexpiredtokens, cleanup_auth_data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Only preview cleanup_auth_data result. Built-in commands "
                "clearsessions/flushexpiredtokens are skipped in dry-run mode."
            ),
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))

        self.stdout.write("Running auth maintenance once")
        if dry_run:
            call_command("cleanup_auth_data", dry_run=True)
            return

        call_command("clearsessions")
        call_command("flushexpiredtokens")
        call_command("cleanup_auth_data")
