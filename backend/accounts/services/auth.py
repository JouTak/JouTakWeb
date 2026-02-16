from __future__ import annotations

from dataclasses import dataclass

from accounts.services.account_status import AccountStatusService
from accounts.services.profile import ProfileService
from accounts.transport.schemas import (
    ProfileOut,
    TokenPairOut,
    TokenRefreshIn,
    TokenRefreshOut,
)
from allauth.mfa.adapter import get_adapter as get_mfa_adapter
from allauth.socialaccount.models import SocialAccount
from core.models import UserSessionMeta, UserSessionToken
from django.contrib.auth import get_user_model
from django.contrib.auth import logout as dj_logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from ninja.errors import HttpError
from ninja_jwt.exceptions import TokenError
from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from ninja_jwt.tokens import RefreshToken

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
        extended = ProfileService.get_or_create_extended_profile(user)
        status = AccountStatusService.get_status(user, profile=extended)
        return ProfileOut(
            username=user.username,
            email=user.email,
            has_2fa=has_2fa,
            oauth_providers=providers,
            first_name=getattr(user, "first_name", None) or None,
            last_name=getattr(user, "last_name", None) or None,
            avatar_url=None,
            email_verified=status["email_verified"],
            profile_complete=status["profile_complete"],
            account_active=status["account_active"],
            registration_completed=status["registration_completed"],
            profile_state=status["profile_state"],
            profile_tier=status["profile_tier"],
            blocking_reasons=status["blocking_reasons"],
            personalization_ui_enabled=status["personalization_ui_enabled"],
            personalization_interstitial_enabled=status[
                "personalization_interstitial_enabled"
            ],
            personalization_enforce_enabled=status[
                "personalization_enforce_enabled"
            ],
            missing_fields=status["missing_fields"],
            **ProfileService.serialize_extended_profile(extended),
        )

    @staticmethod
    def change_password(user: User, current: str, new: str) -> None:
        if not user.check_password(current):
            raise HttpError(400, "wrong current password")
        if not (new and new.strip()):
            raise HttpError(400, "new password cannot be empty")
        if current == new:
            raise HttpError(400, "new password must differ from current")
        try:
            validate_password(new, user=user)
        except ValidationError as e:
            raise HttpError(400, "; ".join(e.messages)) from e
        user.set_password(new)
        user.save(update_fields=["password"])

    @staticmethod
    @transaction.atomic
    def refresh_pair(request, payload: TokenRefreshIn) -> TokenRefreshOut:
        try:
            rt = RefreshToken(payload.refresh)
            rt.check_blacklist()
        except TokenError as e:
            raise HttpError(401, "invalid refresh") from e

        old_jti = str(rt.get("jti") or "")
        user_id = rt.get("user_id")
        user = User.objects.filter(pk=user_id).first()
        if not user:
            raise HttpError(401, "invalid user")

        new_refresh = RefreshToken.for_user(user)
        new_jti = str(new_refresh.get("jti") or "")

        old_ot = OutstandingToken.objects.filter(jti=old_jti).first()
        if old_ot:
            BlacklistedToken.objects.get_or_create(token=old_ot)

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

        mapping = (
            UserSessionToken.objects.select_for_update()
            .filter(user=user, refresh_jti=old_jti, revoked_at__isnull=True)
            .first()
        )
        if mapping:
            mapping.refresh_jti = new_jti
            mapping.save(update_fields=["refresh_jti"])
        elif meta:
            UserSessionToken.objects.get_or_create(
                user=user, session_key=meta.session_key, refresh_jti=new_jti
            )

        return TokenRefreshOut(
            refresh=str(new_refresh), access=str(new_refresh.access_token)
        )
