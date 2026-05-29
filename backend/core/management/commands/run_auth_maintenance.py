from __future__ import annotations

import time

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connections

DEFAULT_INTERVAL_SECONDS = 60 * 60 * 24
DEFAULT_DB_WAIT_SECONDS = 60
MIN_INTERVAL_SECONDS = 60


class Command(BaseCommand):
    help = (
        "Run recurring auth/session maintenance using Django management "
        "commands."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run a single maintenance cycle and exit.",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=DEFAULT_INTERVAL_SECONDS,
            help=(
                "Seconds between maintenance cycles when running continuously."
            ),
        )
        parser.add_argument(
            "--db-wait-seconds",
            type=int,
            default=DEFAULT_DB_WAIT_SECONDS,
            help="How long to wait for the database before failing.",
        )

    def handle(self, *args, **options) -> None:
        once = options["once"]
        interval = options["interval"]
        db_wait_seconds = options["db_wait_seconds"]
        verbosity = options["verbosity"]

        if db_wait_seconds < 0:
            raise CommandError("--db-wait-seconds must be >= 0")
        if not once and interval < MIN_INTERVAL_SECONDS:
            raise CommandError(
                f"--interval must be >= {MIN_INTERVAL_SECONDS} seconds"
            )

        self._wait_for_database(db_wait_seconds)

        if once:
            self.stdout.write("Running auth maintenance once")
            try:
                self._run_cycle(verbosity)
            finally:
                connections.close_all()
            return

        self.stdout.write(
            f"Starting auth maintenance loop every {interval} seconds"
        )
        try:
            while True:
                self._run_loop_iteration(verbosity)
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write("Auth maintenance stopped")

    def _wait_for_database(self, timeout_seconds: int) -> None:
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                connections["default"].ensure_connection()
                return
            except Exception as exc:
                if time.monotonic() >= deadline:
                    raise CommandError(
                        "Database is not ready after "
                        f"{timeout_seconds} seconds"
                    ) from exc
                time.sleep(1)

    def _run_loop_iteration(self, verbosity: int) -> None:
        try:
            self._run_cycle(verbosity)
        except Exception as exc:
            self.stderr.write(
                self.style.ERROR(f"auth maintenance cycle failed: {exc}")
            )
        finally:
            connections.close_all()

    def _run_cycle(self, verbosity: int) -> None:
        call_command("clearsessions", verbosity=verbosity)
        call_command("cleanup_auth_data", verbosity=verbosity)
