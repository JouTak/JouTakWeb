from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from accounts.services.personalization import personalization_complete
from allauth.account.models import EmailAddress
from core.models import UserProfile
from django.conf import settings
from django.contrib.auth import get_user_model
from ninja.errors import HttpError

User = get_user_model()
PROFILE_PERSONALIZATION_REQUIRED = "PROFILE_PERSONALIZATION_REQUIRED"
PROFILE_FIELDS_INCOMPLETE = "PROFILE_FIELDS_INCOMPLETE"


@dataclass(slots=True)
class AccountStatusService:
    @staticmethod
    def is_email_verified(user: User) -> bool:
        primary = EmailAddress.objects.filter(user=user, primary=True).first()
        return bool(primary and primary.verified)

    @staticmethod
    def profile_complete(profile: UserProfile) -> tuple[bool, list[str]]:
        return personalization_complete(profile)

    @staticmethod
    def get_status(
        user: User, profile: UserProfile | None = None
    ) -> dict[str, Any]:
        p = profile or UserProfile.objects.get_or_create(user=user)[0]
        email_verified = AccountStatusService.is_email_verified(user)
        complete, missing = AccountStatusService.profile_complete(p)
        profile_state = "personalized" if complete else "basic"
        blocking_reasons: list[str] = []
        if not complete:
            blocking_reasons.append(PROFILE_FIELDS_INCOMPLETE)
        return {
            "email_verified": email_verified,
            "profile_complete": complete,
            # Backward-compat fields: now tied to profile personalization only.
            "account_active": complete,
            "registration_completed": complete,
            "profile_state": profile_state,
            "profile_tier": (
                "advanced" if profile_state == "personalized" else "basic"
            ),
            "blocking_reasons": blocking_reasons,
            "personalization_ui_enabled": bool(
                getattr(settings, "FF_PROFILE_PERSONALIZATION_UI", True)
            ),
            "personalization_interstitial_enabled": bool(
                getattr(
                    settings, "FF_PROFILE_PERSONALIZATION_INTERSTITIAL", True
                )
            ),
            "personalization_enforce_enabled": bool(
                getattr(settings, "FF_PROFILE_PERSONALIZATION_ENFORCE", False)
            ),
            "missing_fields": missing,
        }

    @staticmethod
    def require_personalized_profile(user: User) -> None:
        status = AccountStatusService.get_status(user)
        if not status.get("personalization_enforce_enabled"):
            return
        if status["profile_state"] == "personalized":
            return
        raise HttpError(
            403,
            json.dumps(
                {
                    "detail": (
                        "Profile personalization is required for this action"
                    ),
                    "error_code": PROFILE_PERSONALIZATION_REQUIRED,
                    "blocking_reasons": status.get("blocking_reasons", []),
                },
                ensure_ascii=False,
            ),
        )

    @staticmethod
    def require_active(user: User) -> None:
        # Backward-compat alias
        AccountStatusService.require_personalized_profile(user)
