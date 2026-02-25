from __future__ import annotations

from datetime import datetime

from ninja import Schema


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


# ---------- Profile / Email ----------
class ProfileUpdateIn(Schema):
    first_name: str | None = None
    last_name: str | None = None
    vk_username: str | None = None
    minecraft_nick: str | None = None
    minecraft_has_license: bool | None = None
    is_itmo_student: bool | None = None
    itmo_isu: str | None = None


class EmailStatusOut(Schema):
    email: str | None = None
    verified: bool = False


class ChangeEmailIn(Schema):
    new_email: str


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
    ids: list[str] | None = None
    all_except_current: bool = False
    reason: str | None = None


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
    refresh: str


class TokenRefreshIn(Schema):
    refresh: str


class TokenRefreshOut(Schema):
    refresh: str
    access: str | None = None


class ChangePasswordIn(Schema):
    current_password: str
    new_password: str


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


# ---------- Headless (session token) ----------
class SessionMetaOut(Schema):
    session_token: str


class LoginOut(Schema):
    meta: SessionMetaOut


class LoginIn(Schema):
    username: str
    password: str


class SignupIn(Schema):
    username: str
    email: str | None = None
    password: str


# ---------- OAuth linking ----------
class ProvidersOut(Schema):
    providers: list[dict]


class OAuthLinkOut(Schema):
    authorize_url: str
    method: str
