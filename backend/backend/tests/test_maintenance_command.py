from __future__ import annotations

from io import StringIO
from unittest.mock import call, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase


class RunAuthMaintenanceCommandTests(SimpleTestCase):
    @patch(
        "core.management.commands.run_auth_maintenance."
        "Command._wait_for_database"
    )
    @patch("core.management.commands.run_auth_maintenance.call_command")
    def test_once_runs_built_in_commands_in_order(
        self,
        call_command_mock,
        wait_for_database_mock,
    ) -> None:
        stdout = StringIO()

        call_command("run_auth_maintenance", "--once", stdout=stdout)

        wait_for_database_mock.assert_called_once_with(60)
        call_command_mock.assert_has_calls(
            [
                call("clearsessions", verbosity=1),
                call("cleanup_auth_data", verbosity=1),
            ]
        )
        self.assertIn("Running auth maintenance once", stdout.getvalue())

    def test_rejects_short_interval_in_loop_mode(self) -> None:
        with self.assertRaisesMessage(
            CommandError,
            "--interval must be >= 60 seconds",
        ):
            call_command("run_auth_maintenance", "--interval", "59")
