from __future__ import annotations

from dataclasses import dataclass

from allauth.account.forms import SignupForm
from allauth.account.utils import perform_login
from allauth.headless import app_settings as allauth_headless_settings
from django.contrib.auth import authenticate
from django.http import HttpRequest
from ninja.errors import HttpError


@dataclass(slots=True)
class HeadlessService:
    @staticmethod
    def issue_session_token(request: HttpRequest) -> str:
        return allauth_headless_settings.TOKEN_STRATEGY.create_session_token(
            request
        )

    @staticmethod
    def login(
        request: HttpRequest,
        username: str,
        password: str,
    ) -> str:
        user = authenticate(
            request, username=username.strip(), password=password
        )
        if not user:
            raise HttpError(400, "invalid credentials")
        perform_login(request, user)
        return HeadlessService.issue_session_token(request)

    @staticmethod
    def signup(
        request: HttpRequest,
        username: str,
        email: str | None,
        password: str,
    ) -> str:
        form = SignupForm(
            data={
                "username": username,
                "email": email or "",
                "password1": password,
                "password2": password,
            }
        )
        if not form.is_valid():
            raise HttpError(400, form.errors.as_json())
        user = form.save(request)
        perform_login(request, user)
        return HeadlessService.issue_session_token(request)
