from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from unittest import TestCase

import yaml


class SmokeInfraConfigTests(TestCase):
    @staticmethod
    def _repo_root() -> Path:
        return Path(__file__).resolve().parents[3]

    def _load_yaml(self, relative_path: str) -> dict[str, object]:
        path = self._repo_root() / relative_path
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    @classmethod
    def _strings(cls, value: object) -> Iterator[str]:
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for child in value.values():
                yield from cls._strings(child)
        elif isinstance(value, list):
            for child in value:
                yield from cls._strings(child)

    def test_compose_backend_is_an_http_debug_server(self) -> None:
        compose = self._load_yaml("compose.yaml")
        backend_env = compose["x-backend-environment"]
        backend = compose["services"]["backend"]

        self.assertEqual(
            backend_env["DJANGO_SETTINGS_MODULE"],
            "backend.settings.dev",
        )
        self.assertEqual(backend_env["DJANGO_DEBUG"], "true")
        self.assertEqual(
            backend_env["EMAIL_BACKEND"],
            "django.core.mail.backends.console.EmailBackend",
        )
        self.assertEqual(backend_env["SECURE_SSL_REDIRECT"], "false")
        for setting in (
            "SESSION_COOKIE_SECURE",
            "CSRF_COOKIE_SECURE",
            "JWT_REFRESH_COOKIE_SECURE",
        ):
            self.assertEqual(backend_env[setting], "false")

        self.assertEqual(
            backend["command"],
            ["python", "manage.py", "runserver", "0.0.0.0:8000"],
        )
        self.assertEqual(backend_env["MEDIA_ROOT"], "/app/media")
        self.assertIn("media_data:/app/media", backend["volumes"])
        self.assertIn(
            "os.access('/app/media', os.W_OK)",
            backend["healthcheck"]["test"][-1],
        )

    def test_compose_interpolations_all_have_development_defaults(
        self,
    ) -> None:
        compose = self._load_yaml("compose.yaml")
        interpolation_pattern = re.compile(r"(?<!\$)\$\{([^}]+)\}")
        interpolations = [
            match
            for value in self._strings(compose)
            for match in interpolation_pattern.findall(value)
        ]

        self.assertTrue(interpolations)
        self.assertEqual(
            [value for value in interpolations if ":-" not in value],
            [],
            "Development Compose must not require a pre-existing .env file",
        )

        database = compose["services"]["db"]["environment"]
        self.assertEqual(
            database["POSTGRES_DB"],
            "${DEV_POSTGRES_DB:-joutak}",
        )
        self.assertEqual(
            database["POSTGRES_USER"],
            "${DEV_POSTGRES_USER:-joutak}",
        )
        self.assertEqual(
            database["POSTGRES_PASSWORD"],
            "${DEV_POSTGRES_PASSWORD:-joutak}",
        )

    def test_compose_frontend_uses_vite_dev_target_and_backend_proxy(
        self,
    ) -> None:
        compose = self._load_yaml("compose.yaml")
        frontend = compose["services"]["frontend"]

        self.assertEqual(frontend["build"]["target"], "dev")
        self.assertEqual(
            frontend["environment"]["DEV_BACKEND_PROXY_TARGET"],
            "http://backend:8000",
        )

    def test_ci_smokes_zero_config_stack_once(self) -> None:
        workflow = self._load_yaml(".github/workflows/CI.yml")
        smoke_job = workflow["jobs"]["smoke_stack"]

        self.assertNotIn(
            "env",
            smoke_job,
            "Smoke must exercise the documented zero-config flow",
        )
        matching_steps = [
            step
            for step in smoke_job["steps"]
            if step.get("name")
            == "Run documented zero-config development stack"
        ]
        self.assertEqual(len(matching_steps), 1)

        smoke_step = matching_steps[0]
        self.assertNotIn("env", smoke_step)
        command = smoke_step["run"]
        self.assertNotIn(".env", command)
        self.assertEqual(
            command.count("docker compose -f compose.yaml up -d --build"),
            1,
        )

        all_commands = "\n".join(
            step.get("run", "") for step in smoke_job["steps"]
        )
        self.assertEqual(
            all_commands.count("uv run python scripts/smoke_stack.py"),
            1,
        )
