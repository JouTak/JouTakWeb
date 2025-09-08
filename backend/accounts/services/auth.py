from __future__ import annotations
from dataclasses import dataclass
from django.contrib.auth import get_user_model, logout as dj_logout
from ninja.errors import HttpError
from ninja_jwt.tokens import RefreshToken
from allauth.mfa.adapter import get_adapter as get_mfa_adapter
from allauth.socialaccount.models import SocialAccount
from allauth.account.models import EmailAddress
from core.models import UserSessionMeta, UserSessionToken
from accounts.transport.schemas import (
    TokenPairOut,
    TokenRefreshIn,
    TokenRefreshOut,
    ProfileOut,
)

User = get_user_model()


@dataclass(slots=True)
class AuthService:
    @staticmethod
    def issue_pair_for_session(request, user: User) -> TokenPairOut:
        if not getattr(user, "is_authenticated", False):
            raise HttpError(401, "Not authenticated")
        token = request.headers.get("X-Session-Token") or ""
        dj_key = request.session.session_key or ""

        meta = (
            UserSessionMeta.objects.filter(
                user=user, session_token=token
            ).first()
            or UserSessionMeta.objects.filter(
                user=user, session_key=dj_key
            ).first()
        )
        if not meta:
            meta = UserSessionMeta.objects.create(
                user=user,
                session_key=dj_key or token,
                session_token=token or None,
            )
        if dj_key and meta.session_key != dj_key:
            meta.session_key = dj_key
            meta.save(update_fields=["session_key"])

        rt = RefreshToken.for_user(user)
        at = rt.access_token

        UserSessionToken.objects.get_or_create(
            user=user, session_key=meta.session_key, refresh_jti=str(rt["jti"])
        )
        return TokenPairOut(access=str(at), refresh=str(rt))

    @staticmethod
    def logout_current(request) -> None:
        dj_logout(request)

    @staticmethod
    def profile(user: User) -> ProfileOut:
        if not user or not getattr(user, "is_authenticated", False):
            raise HttpError(401, "Not authenticated")
        has_2fa = get_mfa_adapter().is_mfa_enabled(user)
        providers = list(
            SocialAccount.objects.filter(user=user).values_list(
                "provider", flat=True
            )
        )
        primary = EmailAddress.objects.filter(user=user, primary=True).first()
        return ProfileOut(
            username=user.username,
            email=user.email,
            has_2fa=has_2fa,
            oauth_providers=providers,
            first_name=getattr(user, "first_name", None) or None,
            last_name=getattr(user, "last_name", None) or None,
            avatar_url=None,
            email_verified=bool(primary and primary.verified),
        )

    @staticmethod
    def change_password(user: User, current: str, new: str) -> None:
        from django.core.exceptions import ValidationError
        from django.contrib.auth.password_validation import validate_password

        if not user.check_password(current):
            raise HttpError(400, "wrong current password")
        if not (new and new.strip()):
            raise HttpError(400, "new password cannot be empty")
        if current == new:
            raise HttpError(400, "new password must differ from current")
        try:
            validate_password(new, user=user)
        except ValidationError as e:
            raise HttpError(400, "; ".join(e.messages))
        user.set_password(new)
        user.save(update_fields=["password"])

    @staticmethod
    def refresh_pair(payload: TokenRefreshIn) -> TokenRefreshOut:
        try:
            rt = RefreshToken(payload.refresh)
        except Exception:
            raise HttpError(401, "invalid refresh")
        user = User.objects.filter(pk=rt.get("user_id")).first()
        if not user:
            raise HttpError(401, "invalid user")
        new_refresh = RefreshToken.for_user(user)
        return TokenRefreshOut(
            refresh=str(new_refresh), access=str(rt.access_token)
        )
