from __future__ import annotations

from dataclasses import dataclass

from accounts.services.account_status import AccountStatusService
from accounts.services.profile import ProfileService
from accounts.services.sessions import SessionService
from accounts.transport.schemas import (
    ChangePasswordOut,
    ProfileOut,
    RevokeSessionsIn,
    TokenPairOut,
    TokenRefreshIn,
    TokenRefreshOut,
)
from allauth.account.internal.flows import (
    password_change as password_change_flow,
)
from allauth.core import context
from allauth.headless.account.inputs import ChangePasswordInput
from allauth.mfa.adapter import get_adapter as get_mfa_adapter
from allauth.socialaccount.models import SocialAccount
from core.models import (
    UserSessionMeta,
    UserSessionToken,
    session_token_digest,
)
from django.contrib.auth import get_user_model
from django.contrib.auth import logout as dj_logout
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from ninja.errors import HttpError
from ninja_jwt.exceptions import TokenError
from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from ninja_jwt.tokens import RefreshToken

User = get_user_model()


@dataclass(slots=True)
class AuthService:
    @staticmethod
    def issue_pair_for_session(
        request: HttpRequest,
        user: User,
    ) -> TokenPairOut:
        if not getattr(user, "is_authenticated", False):
            raise HttpError(401, "Not authenticated")
        token = request.headers.get("X-Session-Token") or ""
        token_digest = session_token_digest(token)
        dj_key = request.session.session_key or ""

        meta = (
            UserSessionMeta.objects.filter(
                user=user, session_token_digest=token_digest
            ).first()
            if token_digest
            else None
        ) or (
            UserSessionMeta.objects.filter(
                user=user, session_key=dj_key
            ).first()
            if dj_key
            else None
        )
        if not meta:
            meta = UserSessionMeta.objects.create(
                user=user,
                session_key=dj_key or token,
                session_token_digest=token_digest or None,
            )
        updates: list[str] = []
        if token_digest and not meta.session_token_digest:
            meta.session_token_digest = token_digest
            updates.append("session_token_digest")
        if dj_key and meta.session_key != dj_key:
            meta.session_key = dj_key
            updates.append("session_key")
        if updates:
            meta.save(update_fields=sorted(set(updates)))

        rt = RefreshToken.for_user(user)
        at = rt.access_token

        UserSessionToken.objects.get_or_create(
            user=user, session_key=meta.session_key, refresh_jti=str(rt["jti"])
        )
        return TokenPairOut(access=str(at), refresh=str(rt))

    @staticmethod
    @transaction.atomic
    def logout_current(request: HttpRequest) -> None:
        user = getattr(request, "auth", None) or getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            token = request.headers.get("X-Session-Token") or ""
            token_digest = session_token_digest(token)
            dj_key = request.session.session_key or ""
            meta = (
                UserSessionMeta.objects.filter(
                    user=user, session_token_digest=token_digest
                ).first()
                if token_digest
                else None
            ) or (
                UserSessionMeta.objects.filter(
                    user=user, session_key=dj_key
                ).first()
                if dj_key
                else None
            )
            session_key = dj_key or (meta.session_key if meta else "")
            if session_key:
                now = timezone.now()
                meta_qs = UserSessionMeta.objects.select_for_update()
                meta, _ = meta_qs.get_or_create(
                    user=user,
                    session_key=session_key,
                    defaults={"session_token_digest": token_digest or None},
                )
                updates: list[str] = []
                if token_digest and not meta.session_token_digest:
                    meta.session_token_digest = token_digest
                    updates.append("session_token_digest")
                if not meta.revoked_at:
                    meta.revoked_at = now
                    updates.append("revoked_at")
                if not meta.revoked_reason:
                    meta.revoked_reason = "logout"
                    updates.append("revoked_reason")
                if updates:
                    meta.save(update_fields=sorted(set(updates)))

                mappings = UserSessionToken.objects.select_for_update().filter(
                    user=user,
                    session_key=session_key,
                    revoked_at__isnull=True,
                )
                for mapping in mappings:
                    ot = OutstandingToken.objects.filter(
                        user=user, jti=mapping.refresh_jti
                    ).first()
                    if ot:
                        BlacklistedToken.objects.get_or_create(token=ot)
                    mapping.revoked_at = now
                    mapping.save(update_fields=["revoked_at"])
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
    @transaction.atomic
    def change_password(
        request: HttpRequest,
        user: User,
        current: str,
        new: str,
        *,
        logout_current_session: bool = False,
    ) -> ChangePasswordOut:
        if current == new:
            raise HttpError(400, "new password must differ from current")
        payload = {
            "current_password": current,
            "new_password": new,
        }
        with context.request_context(request):
            form = ChangePasswordInput(payload, user=user)
            if not form.is_valid():
                raise HttpError(400, form.errors.as_json())

        password_change_flow.change_password(
            user, form.cleaned_data["new_password"]
        )
        request.user = user
        password_change_flow.finalize_password_change(request, user)
        SessionService.revoke_bulk(
            request,
            payload=RevokeSessionsIn(
                all_except_current=True,
                reason="password_changed",
            ),
        )
        if logout_current_session:
            AuthService.logout_current(request)
            return ChangePasswordOut(
                ok=True,
                message="password changed; current session logged out",
                logged_out_current_session=True,
                terminated_other_sessions=True,
            )
        return ChangePasswordOut(
            ok=True,
            message="password changed",
            logged_out_current_session=False,
            terminated_other_sessions=True,
        )

    @staticmethod
    @transaction.atomic
    def refresh_pair(
        request: HttpRequest,
        payload: TokenRefreshIn,
    ) -> TokenRefreshOut:
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

        mapping = (
            UserSessionToken.objects.select_for_update()
            .filter(user=user, refresh_jti=old_jti, revoked_at__isnull=True)
            .first()
        )
        if not mapping:
            raise HttpError(401, "invalid refresh")

        request_token = request.headers.get("X-Session-Token") or ""
        if not request_token:
            raise HttpError(401, "session token required for refresh")
        request_token_digest = session_token_digest(request_token)

        request_meta = UserSessionMeta.objects.filter(
            user=user,
            session_token_digest=request_token_digest,
        ).first()
        if not request_meta or not request_meta.session_key:
            raise HttpError(401, "invalid session token")

        if mapping.session_key != request_meta.session_key:
            raise HttpError(401, "invalid refresh")

        current_meta = UserSessionMeta.objects.filter(
            user=user,
            session_key=mapping.session_key,
        ).first()
        if current_meta and current_meta.revoked_at:
            raise HttpError(401, "invalid refresh")

        new_refresh = RefreshToken.for_user(user)
        new_jti = str(new_refresh.get("jti") or "")

        old_ot = OutstandingToken.objects.filter(jti=old_jti).first()
        if old_ot:
            BlacklistedToken.objects.get_or_create(token=old_ot)

        mapping.refresh_jti = new_jti
        mapping.save(update_fields=["refresh_jti"])

        return TokenRefreshOut(
            refresh=str(new_refresh), access=str(new_refresh.access_token)
        )
