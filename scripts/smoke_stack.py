from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(slots=True)
class SmokeResponse:
    status: int
    body: str
    headers: dict[str, str]


def fetch(
    path: str,
    *,
    host: str,
    port: int = 80,
    method: str = "GET",
    data: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> SmokeResponse:
    payload = None
    request_headers = {"Host": host, **(headers or {})}
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = Request(
        f"http://127.0.0.1:{port}{path}",
        data=payload,
        headers=request_headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return SmokeResponse(
                status=response.status,
                body=body,
                headers=dict(response.headers.items()),
            )
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return SmokeResponse(
            status=exc.code,
            body=body,
            headers=dict(exc.headers.items()),
        )
    except URLError as exc:
        raise RuntimeError(f"request failed for {host}{path}: {exc}") from exc


def assert_status(
    response: SmokeResponse,
    *,
    expected: int,
    label: str,
) -> None:
    if response.status != expected:
        raise AssertionError(
            f"{label}: expected {expected}, got {response.status}: "
            f"{response.body[:400]}"
        )


def wait_for_health() -> None:
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            response = fetch(
                "/health/",
                host="api.localhost",
                port=8000,
                timeout=2,
            )
        except RuntimeError:
            time.sleep(2)
            continue
        if response.status == 200 and "Alive" in response.body:
            return
        time.sleep(2)
    raise TimeoutError("backend did not become healthy in time")


def run_smoke() -> None:
    wait_for_health()

    frontend = fetch("/", host="localhost", port=8080)
    assert_status(frontend, expected=200, label="frontend /")

    health = fetch("/health/", host="api.localhost", port=8000)
    assert_status(health, expected=200, label="api health")

    bootstrap = fetch("/bff/bootstrap", host="api.localhost", port=8000)
    assert_status(bootstrap, expected=200, label="bff bootstrap")
    bootstrap_payload = json.loads(bootstrap.body)
    assert "features" in bootstrap_payload
    assert "layout" in bootstrap_payload

    admin_login = fetch(
        "/admin/login/",
        host="admin.localhost",
        port=8000,
    )
    assert_status(admin_login, expected=200, label="admin login")
    assert "JouTak Staff Admin" in admin_login.body

    admin_block = fetch(
        "/bff/bootstrap",
        host="admin.localhost",
        port=8000,
    )
    assert_status(admin_block, expected=403, label="admin host bff block")

    signup = fetch(
        "/api/auth/flow/app/v1/auth/signup",
        host="api.localhost",
        port=8000,
        method="POST",
        headers={
            "X-Client": "app",
            "X-Allauth-Client": "app",
        },
        data={
            "email": f"smoke-{int(time.time())}@example.com",
            "password": "StrongPass123!",
        },
    )
    assert_status(signup, expected=200, label="signup")
    session_token = signup.headers.get("X-Session-Token") or json.loads(
        signup.body
    ).get("meta", {}).get("session_token")
    if not session_token:
        raise AssertionError("signup did not return session token")

    account_summary = fetch(
        "/bff/account/summary",
        host="api.localhost",
        port=8000,
        headers={"X-Session-Token": session_token},
    )
    assert_status(account_summary, expected=200, label="bff account summary")
    account_payload = json.loads(account_summary.body)
    assert account_payload["viewer"]["is_authenticated"] is True


if __name__ == "__main__":
    try:
        run_smoke()
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"Smoke failed: {exc}\n")
        raise SystemExit(1) from exc
