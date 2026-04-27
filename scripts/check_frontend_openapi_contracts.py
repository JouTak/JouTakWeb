from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_SERVICES_DIR = REPO_ROOT / "frontend" / "src" / "services"
DEFAULT_DJANGO_SETTINGS = "backend.settings.dev"
RUN_COMMAND = (
    "PYTHONPATH=backend DJANGO_SETTINGS_MODULE=backend.settings.dev "
    "uv run python scripts/check_frontend_openapi_contracts.py"
)

SESSION_CLIENT_CALL_RE = re.compile(
    r"\b(sessionGet|sessionPost|sessionPatch|sessionDelete)\s*\(\s*"
    r"(?P<quote>[\"'`])(?P<path>/[^\"'`]+)(?P=quote)",
)
BARE_REFRESH_CALL_RE = re.compile(
    r"\bbareClient\.post\s*\(\s*[\"']/auth/refresh[\"']"
)
SESSION_CLIENT_METHODS = {
    "sessionGet": "get",
    "sessionPost": "post",
    "sessionPatch": "patch",
    "sessionDelete": "delete",
}


@dataclass(frozen=True, slots=True)
class FrontendCall:
    method: str
    path: str
    source: str

    @property
    def label(self) -> str:
        return f"{self.method.upper()} {self.path}"


@dataclass(frozen=True, slots=True)
class BodyContract:
    method: str
    path: str
    schema_ref: str

    @property
    def label(self) -> str:
        return f"{self.method.upper()} {self.path}"


@dataclass(frozen=True, slots=True)
class ParameterContract:
    method: str
    path: str
    location: str
    name: str
    schema: dict[str, object]

    @property
    def label(self) -> str:
        return f"{self.method.upper()} {self.path}"


def fail_configuration(message: str) -> NoReturn:
    sys.stderr.write("OpenAPI contract check is not configured.\n")
    sys.stderr.write(f"{message}\n")
    sys.stderr.write(f"Run from repo root:\n  {RUN_COMMAND}\n")
    raise SystemExit(2)


def configure_django() -> None:
    """Initialize Django after the caller provides explicit import settings."""
    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        fail_configuration(
            "DJANGO_SETTINGS_MODULE is missing. "
            f"Expected {DEFAULT_DJANGO_SETTINGS!r} for this check."
        )

    try:
        import django  # noqa: PLC0415

        django.setup()
    except ModuleNotFoundError as exc:
        if exc.name in {"accounts", "backend"}:
            fail_configuration(
                "Backend modules are not importable. "
                "PYTHONPATH must include ./backend."
            )
        raise


def normalize_frontend_path(path: str) -> str:
    if path.startswith("/oauth/link/${"):
        return "/api/oauth/link/{provider}"
    if path.startswith("/account/sessions/${"):
        return "/api/account/sessions/{sid}"
    return f"/api{path}"


def discover_frontend_calls() -> set[FrontendCall]:
    calls: set[FrontendCall] = set()

    for path in sorted(FRONTEND_SERVICES_DIR.rglob("*.js")):
        text = path.read_text(encoding="utf-8")
        source = str(path.relative_to(REPO_ROOT))

        for match in SESSION_CLIENT_CALL_RE.finditer(text):
            calls.add(
                FrontendCall(
                    method=SESSION_CLIENT_METHODS[match.group(1)],
                    path=normalize_frontend_path(match.group("path")),
                    source=source,
                )
            )

        if BARE_REFRESH_CALL_RE.search(text):
            calls.add(
                FrontendCall(
                    method="post",
                    path="/api/auth/refresh",
                    source=source,
                )
            )

    return calls


def load_openapi_schema() -> dict[str, Any]:
    from backend.urls import api  # noqa: PLC0415

    return api.get_openapi_schema()


def build_body_contracts() -> tuple[BodyContract, ...]:
    return (
        BodyContract("post", "/api/account/delete", "DeleteAccountIn"),
        BodyContract("patch", "/api/account/profile", "ProfileUpdateIn"),
        BodyContract(
            "post",
            "/api/account/sessions/bulk",
            "RevokeSessionsIn",
        ),
        BodyContract(
            "post",
            "/api/auth/change_password",
            "ChangePasswordIn",
        ),
        BodyContract("post", "/api/auth/refresh", "TokenRefreshIn"),
    )


def build_parameter_contracts() -> tuple[ParameterContract, ...]:
    from accounts.transport.schemas import (  # noqa: PLC0415
        NEXT_PATH_MAX_LENGTH,
        PROVIDER_ID_MAX_LENGTH,
        PROVIDER_ID_MIN_LENGTH,
        PROVIDER_ID_PATTERN,
        REVOKE_REASON_MAX_LENGTH,
        REVOKE_REASON_PATTERN,
        SESSION_ID_MAX_LENGTH,
    )

    return (
        ParameterContract(
            method="delete",
            path="/api/account/sessions/{sid}",
            location="path",
            name="sid",
            schema={
                "type": "string",
                "minLength": 1,
                "maxLength": SESSION_ID_MAX_LENGTH,
            },
        ),
        ParameterContract(
            method="delete",
            path="/api/account/sessions/{sid}",
            location="query",
            name="reason",
            schema={
                "type": "string",
                "minLength": 1,
                "maxLength": REVOKE_REASON_MAX_LENGTH,
                "pattern": REVOKE_REASON_PATTERN,
            },
        ),
        ParameterContract(
            method="get",
            path="/api/oauth/link/{provider}",
            location="path",
            name="provider",
            schema={
                "type": "string",
                "minLength": PROVIDER_ID_MIN_LENGTH,
                "maxLength": PROVIDER_ID_MAX_LENGTH,
                "pattern": PROVIDER_ID_PATTERN,
            },
        ),
        ParameterContract(
            method="get",
            path="/api/oauth/link/{provider}",
            location="query",
            name="next",
            schema={"type": "string", "maxLength": NEXT_PATH_MAX_LENGTH},
        ),
    )


def operation(schema: dict[str, Any], method: str, path: str) -> dict | None:
    return schema.get("paths", {}).get(path, {}).get(method)


def parameter(
    operation_schema: dict[str, Any],
    location: str,
    name: str,
) -> dict | None:
    for param in operation_schema.get("parameters", []):
        if param.get("in") == location and param.get("name") == name:
            return param
    return None


def request_body_ref(operation_schema: dict[str, Any]) -> str | None:
    schema = (
        operation_schema.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    ref = schema.get("$ref")
    return str(ref).rsplit("/", 1)[-1] if ref else None


def response_codes(operation_schema: dict[str, Any]) -> set[int]:
    return {int(code) for code in operation_schema.get("responses", {})}


def validate_frontend_calls(
    schema: dict[str, Any],
    calls: set[FrontendCall],
) -> list[str]:
    errors: list[str] = []

    for call in sorted(calls, key=lambda item: item.label):
        if operation(schema, call.method, call.path) is None:
            errors.append(f"{call.source}: {call.label} missing in OpenAPI")

    return errors


def validate_body_contracts(
    schema: dict[str, Any],
    contracts: tuple[BodyContract, ...],
) -> list[str]:
    errors: list[str] = []

    for contract in contracts:
        op = operation(schema, contract.method, contract.path)
        if op is None:
            continue

        actual_ref = request_body_ref(op)
        if actual_ref != contract.schema_ref:
            errors.append(
                f"{contract.label} body schema: expected "
                f"{contract.schema_ref}, got {actual_ref or 'none'}"
            )

    return errors


def validate_schema_boundary_responses(
    schema: dict[str, Any],
    body_contracts: tuple[BodyContract, ...],
) -> list[str]:
    errors: list[str] = []
    contracts = {
        ("delete", "/api/account/sessions/{sid}"),
        ("get", "/api/oauth/link/{provider}"),
        *((contract.method, contract.path) for contract in body_contracts),
    }

    for method, path in sorted(contracts):
        op = operation(schema, method, path)
        if op is None:
            continue
        if 422 not in response_codes(op):
            errors.append(f"{method.upper()} {path}: response 422 missing")

    return errors


def validate_parameter_contracts(
    schema: dict[str, Any],
    contracts: tuple[ParameterContract, ...],
) -> list[str]:
    errors: list[str] = []

    for contract in contracts:
        op = operation(schema, contract.method, contract.path)
        if op is None:
            continue

        param = parameter(op, contract.location, contract.name)
        if param is None:
            errors.append(
                f"{contract.label}: {contract.location} "
                f"{contract.name} missing"
            )
            continue

        actual_schema = param.get("schema") or {}
        for key, expected_value in contract.schema.items():
            actual_value = actual_schema.get(key)
            if actual_value != expected_value:
                errors.append(
                    f"{contract.label}: {contract.location} "
                    f"{contract.name} schema {key} expected "
                    f"{expected_value!r}, got {actual_value!r}"
                )

    return errors


def run_contract_checks() -> tuple[int, list[str]]:
    schema = load_openapi_schema()
    calls = discover_frontend_calls()
    body_contracts = build_body_contracts()
    parameter_contracts = build_parameter_contracts()

    errors = [
        *validate_frontend_calls(schema, calls),
        *validate_body_contracts(schema, body_contracts),
        *validate_schema_boundary_responses(schema, body_contracts),
        *validate_parameter_contracts(schema, parameter_contracts),
    ]

    return len(calls), errors


def main() -> int:
    configure_django()
    calls_count, errors = run_contract_checks()

    if errors:
        sys.stderr.write("OpenAPI contract check failed:\n")
        for error in errors:
            sys.stderr.write(f"- {error}\n")
        return 1

    sys.stdout.write(
        f"OpenAPI contract check passed: {calls_count} frontend Ninja calls\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
