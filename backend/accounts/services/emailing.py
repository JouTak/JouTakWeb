from __future__ import annotations

from allauth.account import app_settings as allauth_account_settings
from allauth.account.adapter import get_adapter as get_account_adapter
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpRequest
from ninja.errors import HttpError

User = get_user_model()


class EmailService:
    @staticmethod
    def _clean_email(new_email: str) -> str:
        try:
            cleaned = get_account_adapter().clean_email(new_email or "")
        except ValidationError as e:
            raise HttpError(400, "Invalid email") from e

        email = (cleaned or "").strip().lower()
        try:
            validate_email(email)
        except ValidationError as e:
            raise HttpError(400, "Invalid email") from e
        if not email:
            raise HttpError(400, "Invalid email")
        return email

    @staticmethod
    def status(user: User) -> dict:
        primary = EmailAddress.objects.filter(user=user, primary=True).first()
        email = (primary.email if primary else (user.email or "")) or ""
        verified = bool(primary and primary.verified)
        return {"email": email, "verified": verified}

    @staticmethod
    def request_change(
        request: HttpRequest,
        user: User,
        *,
        new_email: str,
    ) -> None:
        email = EmailService._clean_email(new_email)

        primary = EmailAddress.objects.filter(user=user, primary=True).first()
        current = (primary.email if primary else user.email) or ""
        if email == (current or "").lower():
            return

        if allauth_account_settings.UNIQUE_EMAIL:
            exists_verified_other = (
                EmailAddress.objects.filter(email__iexact=email, verified=True)
                .exclude(user=user)
                .exists()
            )
            if exists_verified_other:
                raise HttpError(
                    400, "Этот email уже используется другим аккаунтом"
                )

        # Keep at most one pending target to avoid stale/unexpected resends.
        EmailAddress.objects.filter(
            user=user, verified=False, primary=False
        ).exclude(email__iexact=email).delete()

        existing = (
            EmailAddress.objects.filter(user=user, email__iexact=email)
            .order_by("-verified", "-primary", "-id")
            .first()
        )
        if existing:
            fields: list[str] = []
            if existing.email != email:
                existing.email = email
                fields.append("email")
            if existing.primary:
                existing.primary = False
                fields.append("primary")
            if fields:
                existing.save(update_fields=fields)
            addr = existing
        else:
            addr = EmailAddress.objects.create(
                user=user,
                email=email,
                verified=False,
                primary=False,
            )
        addr.send_confirmation(request)

    @staticmethod
    def resend_confirmation(request: HttpRequest, user: User) -> None:
        primary = EmailAddress.objects.filter(user=user, primary=True).first()
        target = (
            primary
            if (primary and not primary.verified)
            else (
                EmailAddress.objects.filter(user=user, verified=False)
                .order_by("-id")
                .first()
            )
        )
        if not target:
            return
        target.send_confirmation(request)
