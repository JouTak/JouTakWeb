from __future__ import annotations

import json
from uuid import uuid4

from django.test import TestCase


class APITestCase(TestCase):
    api_root = "/api"
    default_password = "StrongPass123!"

    def setUp(self):
        super().setUp()
        self.client.defaults["HTTP_X_CLIENT"] = "app"
        self.client.defaults["HTTP_X_ALLAUTH_CLIENT"] = "app"

    def api(self, path: str) -> str:
        return f"{self.api_root}{path}"

    def post_json(self, path: str, payload: dict | None = None, **headers):
        return self.client.post(
            self.api(path),
            data=json.dumps(payload or {}),
            content_type="application/json",
            **headers,
        )

    def patch_json(self, path: str, payload: dict | None = None, **headers):
        return self.client.patch(
            self.api(path),
            data=json.dumps(payload or {}),
            content_type="application/json",
            **headers,
        )

    def delete_json(self, path: str, payload: dict | None = None, **headers):
        return self.client.delete(
            self.api(path),
            data=json.dumps(payload or {}),
            content_type="application/json",
            **headers,
        )

    def unique_username(self, prefix: str = "user") -> str:
        return f"{prefix}_{uuid4().hex[:8]}"

    def unique_email(self, prefix: str = "user") -> str:
        return f"{prefix}_{uuid4().hex[:8]}@example.com"

    def signup(
        self, *, username: str, email: str, password: str | None = None
    ):
        password = password or self.default_password
        return self.post_json(
            "/auth/signup",
            {"username": username, "email": email, "password": password},
        )

    def login(self, *, username: str, password: str | None = None):
        password = password or self.default_password
        return self.post_json(
            "/auth/login",
            {"username": username, "password": password},
        )

    @staticmethod
    def session_token(response) -> str | None:
        data = response.json() if response.content else {}
        return response.headers.get("X-Session-Token") or (
            data.get("meta") or {}
        ).get("session_token")

    def auth_headers(self, session_token: str) -> dict[str, str]:
        return {"HTTP_X_SESSION_TOKEN": session_token}

    def signup_and_auth(
        self, *, username: str | None = None, email: str | None = None
    ):
        username = username or self.unique_username("signup")
        email = email or self.unique_email("signup")
        response = self.signup(username=username, email=email)
        self.assertEqual(response.status_code, 200, response.content)
        token = self.session_token(response)
        self.assertTrue(token)
        return {
            "username": username,
            "email": email,
            "session_token": token,
        }
