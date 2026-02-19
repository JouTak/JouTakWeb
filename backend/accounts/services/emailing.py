from __future__ import annotations

from allauth.account.adapter import get_adapter as get_account_adapter
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from ninja.errors import HttpError

User = get_user_model()


class EmailService:
    @staticmethod
    def status(user: User) -> dict:
        primary = EmailAddress.objects.filter(user=user, primary=True).first()
        email = (primary.email if primary else (user.email or "")) or ""
        verified = bool(primary and primary.verified)
        return {"email": email, "verified": verified}

    @staticmethod
    def request_change(request, user: User, *, new_email: str) -> None:
        try:
            email = get_account_adapter().clean_email(new_email or "")
        except ValidationError as e:
            raise HttpError(400, "Invalid email") from e

        email = (email or "").strip()
        try:
            validate_email(email)
        except ValidationError as e:
            raise HttpError(400, "Invalid email") from e
        if not email:
            raise HttpError(400, "Invalid email")

        primary = EmailAddress.objects.filter(user=user, primary=True).first()
        current = (primary.email if primary else user.email) or ""
        if email.lower() == (current or "").lower():
            return

        if getattr(settings, "ACCOUNT_UNIQUE_EMAIL", False):
            exists_verified_other = (
                EmailAddress.objects.filter(email__iexact=email, verified=True)
                .exclude(user=user)
                .exists()
            )
            if exists_verified_other:
                raise HttpError(
                    400, "Этот email уже используется другим аккаунтом"
                )

        addr, _ = EmailAddress.objects.get_or_create(
            user=user,
            email=email,
            defaults={"verified": False, "primary": False},
        )
        addr.send_confirmation(request)

    @staticmethod
    def resend_confirmation(request, user: User) -> None:
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
