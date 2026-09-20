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

    def _load_env_example(self) -> dict[str, str]:
        values: dict[str, str] = {}
        path = self._repo_root() / ".env.example"
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", maxsplit=1)
            values[key.strip()] = value.strip()
        return values

    @staticmethod
    def _labels(service: dict[str, object]) -> dict[str, str]:
        labels = service["deploy"]["labels"]
        return dict((str(label).split("=", maxsplit=1) for label in labels))

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
        backend_env = compose["x-backend-environment"]
        frontend = compose["services"]["frontend"]

        self.assertEqual(
            backend_env["DJANGO_API_HOSTS"],
            "${DEV_DJANGO_API_HOSTS:-joutak.localhost,api.localhost}",
        )
        self.assertEqual(frontend["build"]["target"], "dev")
        self.assertEqual(
            frontend["environment"]["DEV_BACKEND_PROXY_TARGET"],
            "http://backend:8000",
        )

        expected_webauthn = {
            "WEBAUTHN_RP_ID": "${DEV_WEBAUTHN_RP_ID:-localhost}",
            "WEBAUTHN_RP_NAME": (
                "${DEV_WEBAUTHN_RP_NAME:-JouTak Development}"
            ),
            "WEBAUTHN_ACCOUNT_ORIGINS": (
                "${DEV_WEBAUTHN_ACCOUNT_ORIGINS:-http://localhost,"
                "http://localhost:5173,http://joutak.localhost}"
            ),
            "WEBAUTHN_ADMIN_ORIGINS": (
                "${DEV_WEBAUTHN_ADMIN_ORIGINS:-http://admin.localhost,"
                "http://admin.localhost:8000}"
            ),
            "WEBAUTHN_ALLOWED_ORIGINS": (
                "${DEV_WEBAUTHN_ALLOWED_ORIGINS:-http://localhost,"
                "http://localhost:5173,http://joutak.localhost,"
                "http://admin.localhost,http://admin.localhost:8000}"
            ),
        }
        for setting, expected in expected_webauthn.items():
            self.assertEqual(backend_env[setting], expected)

    def test_local_proxy_mirrors_root_host_backend_routes(self) -> None:
        proxy_config = (
            self._repo_root() / "local-proxy.nginx.conf"
        ).read_text(encoding="utf-8")
        same_origin_location = (
            "location ~ ^/(?:(?:api|bff|accounts|media|admin)(?:/|$)|"
            "health/?$)"
        )
        admin_static_denial = "location ~ ^/static/admin(?:/|$) {"

        self.assertIn("server_name localhost joutak.localhost;", proxy_config)
        self.assertIn(same_origin_location, proxy_config)
        self.assertIn(admin_static_denial, proxy_config)
        self.assertLess(
            proxy_config.index(admin_static_denial),
            proxy_config.index(same_origin_location),
        )
        denial_start = proxy_config.index(admin_static_denial)
        denial_end = proxy_config.index("}", denial_start)
        self.assertIn("return 403;", proxy_config[denial_start:denial_end])
        self.assertIn("proxy_pass http://$backend_upstream;", proxy_config)
        self.assertNotIn("proxy_pass http://$backend_upstream/;", proxy_config)
        self.assertNotIn("rewrite ", proxy_config)
        self.assertEqual(
            proxy_config.count("proxy_set_header Host $http_host;"),
            3,
        )
        self.assertNotIn("proxy_set_header Host $host;", proxy_config)

    def test_production_env_uses_same_origin_api_and_host_only_session(
        self,
    ) -> None:
        env = self._load_env_example()

        self.assertEqual(env["PUBLIC_API_URL"], "https://joutak.ru/api")
        self.assertEqual(env["TRAEFIK_ACME_EMAIL"], "")
        self.assertEqual(
            env["DJANGO_API_HOSTS"],
            "joutak.ru,api.joutak.ru",
        )
        self.assertEqual(env["CORS_ALLOWED_ORIGINS"], "https://joutak.ru")
        self.assertEqual(
            env["DJANGO_CSRF_TRUSTED_ORIGINS"],
            "https://joutak.ru",
        )
        self.assertEqual(
            env["SESSION_COOKIE_NAME"],
            "__Host-joutak_session",
        )
        self.assertEqual(env["SESSION_COOKIE_SAMESITE"], "Lax")
        self.assertEqual(env["CSRF_COOKIE_SAMESITE"], "Lax")
        self.assertEqual(env["CACHE_MAX_ENTRIES"], "100000")
        self.assertNotIn("SESSION_COOKIE_DOMAIN", env)
        self.assertNotIn("CSRF_COOKIE_DOMAIN", env)
        self.assertNotIn("JWT_REFRESH_COOKIE_DOMAIN", env)
        self.assertEqual(env["WEBAUTHN_RP_ID"], "joutak.ru")
        self.assertEqual(env["WEBAUTHN_RP_NAME"], "JouTak")
        self.assertEqual(
            env["WEBAUTHN_ACCOUNT_ORIGINS"],
            "https://joutak.ru",
        )
        self.assertEqual(
            env["WEBAUTHN_ADMIN_ORIGINS"],
            "https://admin.joutak.ru",
        )
        self.assertEqual(
            env["WEBAUTHN_ALLOWED_ORIGINS"],
            "https://joutak.ru,https://admin.joutak.ru",
        )

    def test_production_compose_manifests_forward_webauthn_policy(
        self,
    ) -> None:
        for manifest in ("docker-compose.yml", "docker-compose.images.yml"):
            compose = self._load_yaml(manifest)
            backend_env = compose["x-backend-environment"]
            for setting in ("DJANGO_ADMIN_HOSTS", "DJANGO_API_HOSTS"):
                self.assertIn(setting, backend_env, manifest)
                self.assertIn("${", backend_env[setting], manifest)
            for setting in (
                "WEBAUTHN_RP_ID",
                "WEBAUTHN_RP_NAME",
                "WEBAUTHN_ACCOUNT_ORIGINS",
                "WEBAUTHN_ADMIN_ORIGINS",
                "WEBAUTHN_ALLOWED_ORIGINS",
            ):
                self.assertIn(setting, backend_env, manifest)
                self.assertIn(":?", backend_env[setting], manifest)

    def test_production_manifests_forward_safe_cache_capacity(self) -> None:
        for manifest in (
            "docker-compose.yml",
            "docker-compose.images.yml",
            "docker-compose.stack.yml",
        ):
            compose = self._load_yaml(manifest)
            backend_env = compose["x-backend-environment"]

            self.assertEqual(
                backend_env["CACHE_MAX_ENTRIES"],
                "${CACHE_MAX_ENTRIES:-100000}",
                manifest,
            )

    def test_backend_entrypoint_fails_if_shared_cache_table_setup_fails(
        self,
    ) -> None:
        entrypoint = (
            self._repo_root() / "backend/docker-entrypoint.sh"
        ).read_text(encoding="utf-8")
        cache_command = "python manage.py createcachetable --database default"

        self.assertEqual(entrypoint.count(cache_command), 1)
        command_line = next(
            line.strip()
            for line in entrypoint.splitlines()
            if cache_command in line
        )
        self.assertEqual(command_line, cache_command)
        self.assertNotIn("|| true", command_line)
        self.assertNotIn("2>/dev/null", command_line)

    def test_swarm_manifest_uses_the_traefik_v3_swarm_provider(
        self,
    ) -> None:
        stack = self._load_yaml("docker-compose.stack.yml")
        traefik = stack["services"]["traefik"]
        command = set(traefik["command"])

        self.assertIn("--providers.swarm=true", command)
        self.assertIn("--providers.swarm.exposedbydefault=false", command)
        self.assertFalse(
            any("providers.docker.swarmMode" in value for value in command)
        )
        self.assertIn(
            "node.role == manager",
            traefik["deploy"]["placement"]["constraints"],
        )
        for option in (
            "--certificatesresolvers.le.acme.storage=/letsencrypt/acme.json",
            "--certificatesresolvers.le.acme.httpchallenge=true",
            "--certificatesresolvers.le.acme.httpchallenge.entrypoint=web",
        ):
            self.assertIn(option, command)
        self.assertTrue(
            any(
                option.startswith("--certificatesresolvers.le.acme.email=${")
                for option in command
            )
        )

    def test_swarm_routes_same_origin_backend_paths_before_the_spa(
        self,
    ) -> None:
        stack = self._load_yaml("docker-compose.stack.yml")
        backend_labels = self._labels(stack["services"]["backend"])
        frontend_labels = self._labels(stack["services"]["frontend"])
        root_rule = backend_labels[
            "traefik.http.routers.backend-root-sec.rule"
        ]

        self.assertIn("Host(`joutak.ru`)", root_rule)
        for prefix in ("api", "bff", "accounts", "media"):
            self.assertIn(f"Path(`/{prefix}`)", root_rule)
            self.assertIn(f"PathPrefix(`/{prefix}/`)", root_rule)
        for path in ("/health", "/health/"):
            self.assertIn(f"Path(`{path}`)", root_rule)

        # Root /admin must reach HostRoutingMiddleware and be denied there;
        # otherwise the frontend catch-all would return index.html with 200.
        self.assertIn("Path(`/admin`)", root_rule)
        self.assertIn("PathPrefix(`/admin/`)", root_rule)
        self.assertIn("Path(`/static/admin`)", root_rule)
        self.assertIn("PathPrefix(`/static/admin/`)", root_rule)
        self.assertFalse(
            any("stripprefix" in key.casefold() for key in backend_labels)
        )

        backend_priority = int(
            backend_labels["traefik.http.routers.backend-root-sec.priority"]
        )
        frontend_priority = int(
            frontend_labels["traefik.http.routers.frontend-sec.priority"]
        )
        self.assertGreater(backend_priority, frontend_priority)
        self.assertEqual(
            backend_labels["traefik.http.routers.backend-root-sec.service"],
            "backend",
        )
        self.assertEqual(
            backend_labels["traefik.http.routers.backend-admin-sec.rule"],
            "Host(`admin.joutak.ru`)",
        )

    def test_swarm_defines_the_https_redirect_middleware_it_uses(
        self,
    ) -> None:
        stack = self._load_yaml("docker-compose.stack.yml")
        backend_labels = self._labels(stack["services"]["backend"])

        self.assertEqual(
            backend_labels[
                "traefik.http.middlewares.redirect-to-https."
                "redirectscheme.scheme"
            ],
            "https",
        )
        self.assertEqual(
            backend_labels[
                "traefik.http.middlewares.redirect-to-https."
                "redirectscheme.permanent"
            ],
            "true",
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
