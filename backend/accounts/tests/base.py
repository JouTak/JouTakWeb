from __future__ import annotations

import json
from uuid import uuid4

from accounts.services.email_addresses import sync_user_email_address
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase
from django.test.utils import override_settings

User = get_user_model()


@override_settings(ACCOUNT_RATE_LIMITS=False)
class APITestCase(TestCase):
    api_root = "/api"
    headless_root = "/api/auth/flow/app/v1"
    default_password = "StrongPass123!"

    def setUp(self) -> None:
        super().setUp()
        self.client.defaults["HTTP_X_CLIENT"] = "app"
        self.client.defaults["HTTP_X_ALLAUTH_CLIENT"] = "app"

    def api(self, path: str) -> str:
        return f"{self.api_root}{path}"

    def headless(self, path: str) -> str:
        return f"{self.headless_root}{path}"

    def post_json(
        self,
        path: str,
        payload: dict[str, object] | None = None,
        **headers: str,
    ) -> HttpResponse:
        return self.client.post(
            self.api(path),
            data=json.dumps(payload or {}),
            content_type="application/json",
            **headers,
        )

    def patch_json(
        self,
        path: str,
        payload: dict[str, object] | None = None,
        **headers: str,
    ) -> HttpResponse:
        return self.client.patch(
            self.api(path),
            data=json.dumps(payload or {}),
            content_type="application/json",
            **headers,
        )

    def delete_json(
        self,
        path: str,
        payload: dict[str, object] | None = None,
        **headers: str,
    ) -> HttpResponse:
        return self.client.delete(
            self.api(path),
            data=json.dumps(payload or {}),
            content_type="application/json",
            **headers,
        )

    def headless_post_json(
        self,
        path: str,
        payload: dict[str, object] | None = None,
        **headers: str,
    ) -> HttpResponse:
        return self.client.post(
            self.headless(path),
            data=json.dumps(payload or {}),
            content_type="application/json",
            **headers,
        )

    def headless_put_json(
        self,
        path: str,
        payload: dict[str, object] | None = None,
        **headers: str,
    ) -> HttpResponse:
        return self.client.put(
            self.headless(path),
            data=json.dumps(payload or {}),
            content_type="application/json",
            **headers,
        )

    def unique_username(self, prefix: str = "user") -> str:
        return f"{prefix}_{uuid4().hex[:8]}"

    def unique_email(self, prefix: str = "user") -> str:
        return f"{prefix}_{uuid4().hex[:8]}@example.com"

    def signup(
        self,
        *,
        email: str,
        password: str | None = None,
        username: str | None = None,
    ) -> HttpResponse:
        password = password or self.default_password
        return self.headless_post_json(
            "/auth/signup",
            {"email": email, "password": password},
        )

    def login(
        self,
        *,
        identifier: str | None = None,
        username: str | None = None,
        email: str | None = None,
        password: str | None = None,
    ) -> HttpResponse:
        password = password or self.default_password
        login_value = (
            str(identifier or "").strip()
            or str(email or "").strip()
            or str(username or "").strip()
        )
        return self.headless_post_json(
            "/auth/login",
            {"username": login_value, "password": password},
        )

    @staticmethod
    def session_token(response: HttpResponse) -> str | None:
        data = response.json() if response.content else {}
        return response.headers.get("X-Session-Token") or (
            data.get("meta") or {}
        ).get("session_token")

    def auth_headers(self, session_token: str) -> dict[str, str]:
        return {"HTTP_X_SESSION_TOKEN": session_token}

    def signup_and_auth(
        self, *, username: str | None = None, email: str | None = None
    ) -> dict[str, str]:
        email = email or self.unique_email("signup")
        response = self.signup(email=email, username=username)
        self.assertEqual(response.status_code, 200, response.content)
        token = self.session_token(response)
        self.assertTrue(token)
        user = User.objects.get(email=email.lower())
        token_value = token or ""
        return {
            "username": user.username,
            "email": email,
            "session_token": token_value,
        }

    def create_legacy_user(
        self,
        *,
        username: str | None = None,
        email: str | None = None,
        password: str | None = None,
    ):
        user = User.objects.create_user(
            username=username or self.unique_username("legacy"),
            email=(email or self.unique_email("legacy")).lower(),
            password=password or self.default_password,
        )
        sync_user_email_address(user)
        return user
