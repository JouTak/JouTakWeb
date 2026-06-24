from __future__ import annotations

from pathlib import Path
from unittest import TestCase

import yaml


class SmokeInfraConfigTests(TestCase):
    @staticmethod
    def _repo_root() -> Path:
        return Path(__file__).resolve().parents[3]

    def test_compose_local_backend_uses_console_email_by_default(self) -> None:
        compose_path = self._repo_root() / "compose.yaml"
        compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))

        backend_env = compose["x-backend-environment"]

        self.assertEqual(
            backend_env["EMAIL_BACKEND"],
            "${EMAIL_BACKEND:-django.core.mail.backends.console.EmailBackend}",
        )

    def test_ci_smoke_jobs_pin_console_email_backend(self) -> None:
        workflow_path = self._repo_root() / ".github" / "workflows" / "CI.yml"
        workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

        smoke_steps = workflow["jobs"]["smoke_stack"]["steps"]
        smoke_step_names = {
            "Run smoke without OTEL endpoints",
            "Restart stack with OTEL endpoints enabled",
            "Dump smoke stack logs on failure",
        }

        selected_steps = [
            step
            for step in smoke_steps
            if step.get("name") in smoke_step_names
        ]

        self.assertEqual(len(selected_steps), 3)
        for step in selected_steps:
            self.assertEqual(
                step["env"]["EMAIL_BACKEND"],
                "django.core.mail.backends.console.EmailBackend",
            )
