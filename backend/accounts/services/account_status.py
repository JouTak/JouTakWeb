from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from accounts.api.errors import raise_structured_error
from accounts.services.personalization import personalization_complete
from allauth.account.models import EmailAddress
from core.models import UserProfile
from django.contrib.auth import get_user_model
from featureflags.registry import get_default_value

User = get_user_model()
PROFILE_PERSONALIZATION_REQUIRED = "PROFILE_PERSONALIZATION_REQUIRED"
PROFILE_FIELDS_INCOMPLETE = "PROFILE_FIELDS_INCOMPLETE"
PERSONALIZATION_CONTEXT_COMPLETE = "complete"
PERSONALIZATION_CONTEXT_NEW_REGISTRATION = "new_registration"
PERSONALIZATION_CONTEXT_LEGACY_REQUIRED = "legacy_required"
PERSONALIZATION_PROMPT_NONE = "none"
PERSONALIZATION_PROMPT_REGISTRATION_SETUP = "registration_setup"
PERSONALIZATION_PROMPT_MIGRATION_NOTICE = "migration_notice"


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
        if complete:
            personalization_context = PERSONALIZATION_CONTEXT_COMPLETE
            personalization_prompt_variant = PERSONALIZATION_PROMPT_NONE
        elif (
            getattr(p, "personalization_origin", "")
            == UserProfile.PERSONALIZATION_ORIGIN_LEGACY
        ):
            personalization_context = PERSONALIZATION_CONTEXT_LEGACY_REQUIRED
            personalization_prompt_variant = (
                PERSONALIZATION_PROMPT_MIGRATION_NOTICE
            )
        else:
            personalization_context = PERSONALIZATION_CONTEXT_NEW_REGISTRATION
            personalization_prompt_variant = (
                PERSONALIZATION_PROMPT_REGISTRATION_SETUP
            )
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
                get_default_value("profile_personalization_ui")
            ),
            "personalization_interstitial_enabled": bool(
                get_default_value("profile_personalization_interstitial")
            ),
            "personalization_enforce_enabled": bool(
                get_default_value("profile_personalization_enforce")
            ),
            "personalization_context": personalization_context,
            "personalization_prompt_variant": personalization_prompt_variant,
            "missing_fields": missing,
        }

    @staticmethod
    def require_personalized_profile(user: User) -> None:
        status = AccountStatusService.get_status(user)
        if not status.get("personalization_enforce_enabled"):
            return
        if status["profile_state"] == "personalized":
            return
        raise_structured_error(
            403,
            detail=("Profile personalization is required for this action"),
            error_code=PROFILE_PERSONALIZATION_REQUIRED,
            blocking_reasons=status.get("blocking_reasons", []),
        )

    @staticmethod
    def require_active(user: User) -> None:
        # Backward-compat alias
        AccountStatusService.require_personalized_profile(user)
