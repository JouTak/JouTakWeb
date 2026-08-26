from __future__ import annotations

import json
import sys
import time
import traceback
from dataclasses import dataclass
from http.client import RemoteDisconnected
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
    retries: int = 0,
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
    for attempt in range(retries + 1):
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
        except (
            RemoteDisconnected,
            ConnectionResetError,
            TimeoutError,
            URLError,
        ) as exc:
            if method == "GET" and attempt < retries:
                time.sleep(1 + attempt)
                continue
            raise RuntimeError(
                f"request failed for {host}{path}: {exc}"
            ) from exc

    raise RuntimeError(f"request failed for {host}{path}: exhausted retries")


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


def response_header(response: SmokeResponse, name: str) -> str:
    expected = name.casefold()
    return next(
        (
            value
            for header, value in response.headers.items()
            if header.casefold() == expected
        ),
        "",
    )


def fetch_step(label: str, path: str, **kwargs) -> SmokeResponse:
    sys.stderr.write(f"Smoke step: {label} -> {kwargs.get('host')}{path}\n")
    return fetch(path, **kwargs)


def wait_for_health() -> None:
    deadline = time.time() + 240
    while time.time() < deadline:
        try:
            response = fetch_step(
                "health through Vite proxy",
                "/health/",
                host="localhost",
                port=5173,
                timeout=2,
                retries=3,
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

    proxied_frontend = fetch_step(
        "frontend through local nginx", "/", host="localhost", retries=3
    )
    assert_status(
        proxied_frontend,
        expected=200,
        label="proxied frontend /",
    )

    vite_frontend = fetch_step(
        "frontend through Vite", "/", host="localhost", port=5173, retries=3
    )
    assert_status(vite_frontend, expected=200, label="Vite frontend /")

    health = fetch_step(
        "API health through Vite proxy",
        "/health/",
        host="localhost",
        port=5173,
        retries=3,
    )
    assert_status(health, expected=200, label="api health")

    nginx_health = fetch_step(
        "API health through local nginx",
        "/health/",
        host="api.localhost",
        retries=3,
    )
    assert_status(nginx_health, expected=200, label="nginx api health")

    bootstrap = fetch_step(
        "bootstrap through Vite proxy",
        "/bff/bootstrap",
        host="localhost",
        port=5173,
        retries=3,
    )
    assert_status(bootstrap, expected=200, label="bff bootstrap")
    bootstrap_payload = json.loads(bootstrap.body)
    assert "viewer" in bootstrap_payload
    assert "features" in bootstrap_payload
    assert "layout" not in bootstrap_payload
    assert "content" not in bootstrap_payload

    itmocraft_page = fetch_step(
        "ITMOcraft page document through Vite proxy",
        "/bff/pages/itmocraft",
        host="localhost",
        port=5173,
        retries=3,
    )
    assert_status(
        itmocraft_page,
        expected=200,
        label="bff ITMOcraft page document",
    )
    page_payload = json.loads(itmocraft_page.body)
    assert page_payload["schema_version"] == 1
    assert page_payload["product"] == {
        "id": "itmocraft",
        "canonical_path": "/",
        "requested_path": "/",
        "is_legacy_alias": False,
    }
    assert page_payload["effective_page_variant"] == "legacy"
    assert page_payload["layout"]["header_variant"] == "legacy"
    assert page_payload["layout"]["footer_variant"] == "legacy"
    assert page_payload["content"]["template"] == "landing-legacy"
    assert response_header(itmocraft_page, "Cache-Control") == (
        "private, no-store"
    )
    assert response_header(itmocraft_page, "Vary") == (
        "Cookie, X-Session-Token, Origin"
    )

    admin_login = fetch_step(
        "admin login through local nginx",
        "/admin/login/",
        host="admin.localhost",
        retries=3,
    )
    assert_status(admin_login, expected=200, label="admin login")
    assert "JouTak Staff Admin" in admin_login.body

    admin_block = fetch_step(
        "admin bootstrap block through local nginx",
        "/bff/bootstrap",
        host="admin.localhost",
        retries=3,
    )
    assert_status(admin_block, expected=403, label="admin host bff block")

    signup = fetch_step(
        "signup through Vite proxy",
        "/api/auth/flow/app/v1/auth/signup",
        host="localhost",
        port=5173,
        method="POST",
        headers={
            "X-Client": "app",
            "X-Allauth-Client": "app",
        },
        data={
            "email": f"smoke-{time.time_ns()}@example.com",
            "password": "StrongPass123!",
        },
    )
    assert_status(signup, expected=200, label="signup")
    session_token = signup.headers.get("X-Session-Token") or json.loads(
        signup.body
    ).get("meta", {}).get("session_token")
    if not session_token:
        raise AssertionError("signup did not return session token")

    jwt_pair = fetch_step(
        "JWT issue through Vite proxy",
        "/api/auth/jwt/from_session",
        host="localhost",
        port=5173,
        method="POST",
        headers={"X-Session-Token": session_token},
        data={},
    )
    assert_status(jwt_pair, expected=200, label="JWT from session")
    jwt_payload = json.loads(jwt_pair.body)
    if not jwt_payload.get("access"):
        raise AssertionError("JWT from session did not return access token")

    set_cookie = response_header(jwt_pair, "Set-Cookie")
    cookie_parts = [part.strip() for part in set_cookie.split(";")]
    refresh_cookie = cookie_parts[0] if cookie_parts else ""
    if not refresh_cookie.startswith("joutak_refresh="):
        raise AssertionError("JWT response did not set joutak_refresh cookie")
    cookie_attributes = {part.casefold() for part in cookie_parts[1:]}
    if "secure" in cookie_attributes:
        raise AssertionError("local refresh cookie must not use Secure")
    for expected_attribute in (
        "httponly",
        "path=/api/auth/refresh",
        "samesite=lax",
    ):
        if expected_attribute not in cookie_attributes:
            raise AssertionError(
                "JWT refresh cookie is missing local attribute: "
                f"{expected_attribute}"
            )
    if any(part.startswith("domain=") for part in cookie_attributes):
        raise AssertionError("local refresh cookie must remain host-only")

    refresh = fetch_step(
        "JWT refresh through Vite proxy",
        "/api/auth/refresh",
        host="localhost",
        port=5173,
        method="POST",
        headers={
            "Cookie": refresh_cookie,
            "X-Session-Token": session_token,
        },
        data={},
    )
    assert_status(refresh, expected=200, label="JWT refresh")
    refresh_payload = json.loads(refresh.body)
    if not refresh_payload.get("access"):
        raise AssertionError("JWT refresh did not return access token")

    account_summary = fetch_step(
        "account summary through Vite proxy",
        "/bff/account/summary",
        host="localhost",
        port=5173,
        headers={"X-Session-Token": session_token},
        retries=3,
    )
    assert_status(account_summary, expected=200, label="bff account summary")
    account_payload = json.loads(account_summary.body)
    assert account_payload["viewer"]["is_authenticated"] is True


if __name__ == "__main__":
    try:
        run_smoke()
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        sys.stderr.write(f"Smoke failed: {exc}\n")
        raise SystemExit(1) from exc
