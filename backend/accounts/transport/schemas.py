from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from ninja import Schema
from pydantic import Field, StringConstraints

SESSION_ID_MAX_LENGTH = 128
REVOKE_REASON_MAX_LENGTH = 64
REVOKE_REASON_PATTERN = r"^[a-zA-Z0-9_.:-]+$"
PROVIDER_ID_MIN_LENGTH = 2
PROVIDER_ID_MAX_LENGTH = 64
PROVIDER_ID_PATTERN = r"^[a-zA-Z0-9_.:-]+$"
NEXT_PATH_MAX_LENGTH = 256

NameStr = Annotated[str, StringConstraints(max_length=150)]
VkUsernameStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        max_length=128,
        pattern=(
            r"^$|^@?[A-Za-z0-9_.-]{2,64}$|"
            r"^(https?://)?(m\.)?vk\.com/[A-Za-z0-9_.-]{2,64}/?$"
        ),
    ),
]
MinecraftNickStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        max_length=16,
        pattern=r"^$|^[A-Za-z0-9_]{3,16}$",
    ),
]
ItmoIsuStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        max_length=20,
        pattern=r"^$|^\d{5,20}$",
    ),
]
SessionIdStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=SESSION_ID_MAX_LENGTH,
    ),
]
RevokeReasonStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=REVOKE_REASON_MAX_LENGTH,
        pattern=REVOKE_REASON_PATTERN,
    ),
]
ProviderIdStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=PROVIDER_ID_MIN_LENGTH,
        max_length=PROVIDER_ID_MAX_LENGTH,
        pattern=PROVIDER_ID_PATTERN,
    ),
]

# ---------- Generic ----------
class FieldErrorItem(Schema):
    message: str
    code: str | None = None


class ErrorOut(Schema):
    detail: str
    code: int | None = None
    error_code: str | None = None
    blocking_reasons: list[str] | None = None
    # Optional structured validation payload (e.g., Django form errors)
    errors: dict[str, list[FieldErrorItem]] | None = None
    # Convenience: first message per field (flat)
    fields: dict[str, str] | None = None


class OkOut(Schema):
    ok: bool
    message: str | None = None


# ---------- Profile ----------
class ProfileUpdateIn(Schema):
    first_name: NameStr | None = None
    last_name: NameStr | None = None
    vk_username: VkUsernameStr | None = None
    minecraft_nick: MinecraftNickStr | None = None
    minecraft_has_license: bool | None = None
    is_itmo_student: bool | None = None
    itmo_isu: ItmoIsuStr | None = None

# ---------- Sessions ----------
class SessionRowOut(Schema):
    id: str | None
    user_agent: str | None
    ip: str | None
    created: datetime | None
    last_seen: datetime | None
    expires: datetime | None
    current: bool
    revoked: bool
    revoked_reason: str | None
    revoked_at: datetime | None


class SessionsOut(Schema):
    sessions: list[SessionRowOut]


class RevokeSessionsIn(Schema):
    ids: list[SessionIdStr] | None = Field(default=None, max_length=100)
    all_except_current: bool = False
    reason: RevokeReasonStr | None = None


class RevokeOut(Schema):
    ok: bool
    # bulk
    reason: str | None = None
    current: str | None = None
    revoked_ids: list[str] | None = None
    skipped_ids: list[str] | None = None
    count: int | None = None
    # single
    id: str | None = None
    revoked_reason: str | None = None
    revoked_at: datetime | None = None


# ---------- Auth / JWT ----------
class TokenPairOut(Schema):
    access: str
    refresh: str | None = None


class TokenRefreshIn(Schema):
    refresh: str | None = None


class TokenRefreshOut(Schema):
    refresh: str | None = None
    access: str | None = None


class ChangePasswordIn(Schema):
    current_password: str
    new_password: str
    logout_current_session: bool = False


class ChangePasswordOut(Schema):
    ok: bool
    message: str | None = None
    logged_out_current_session: bool = False
    terminated_other_sessions: bool = True


class DeleteAccountIn(Schema):
    current_password: str


class ProfileOut(Schema):
    username: str
    email: str
    has_2fa: bool
    oauth_providers: list[str]
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    email_verified: bool = False
    profile_complete: bool = False
    account_active: bool = False
    registration_completed: bool = False
    profile_state: str = "basic"
    profile_tier: str = "basic"
    blocking_reasons: list[str]
    personalization_ui_enabled: bool = True
    personalization_interstitial_enabled: bool = True
    personalization_enforce_enabled: bool = False
    missing_fields: list[str]
    vk_username: str | None = None
    minecraft_nick: str | None = None
    minecraft_has_license: bool | None = None
    is_itmo_student: bool | None = None
    itmo_isu: str | None = None


class AccountStatusOut(Schema):
    email_verified: bool = False
    profile_complete: bool = False
    account_active: bool = False
    registration_completed: bool = False
    profile_state: str = "basic"
    profile_tier: str = "basic"
    blocking_reasons: list[str]
    personalization_ui_enabled: bool = True
    personalization_interstitial_enabled: bool = True
    personalization_enforce_enabled: bool = False
    missing_fields: list[str]


class ProfileUpdateOut(Schema):
    ok: bool
    message: str | None = None
    email_verified: bool = False
    profile_complete: bool = False
    account_active: bool = False
    registration_completed: bool = False
    profile_state: str = "basic"
    profile_tier: str = "basic"
    blocking_reasons: list[str]
    personalization_ui_enabled: bool = True
    personalization_interstitial_enabled: bool = True
    personalization_enforce_enabled: bool = False
    missing_fields: list[str]

# ---------- OAuth linking ----------
class ProviderOut(Schema):
    id: ProviderIdStr
    name: str


class ProvidersOut(Schema):
    providers: list[ProviderOut]


class OAuthLinkOut(Schema):
    authorize_url: str
    method: Literal["GET", "POST"]
