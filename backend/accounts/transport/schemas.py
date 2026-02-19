from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from ninja import Schema


# ---------- Generic ----------
class FieldErrorItem(Schema):
    message: str
    code: Optional[str] = None


class ErrorOut(Schema):
    detail: str
    code: int | None = None
    error_code: Optional[str] = None
    blocking_reasons: Optional[list[str]] = None
    # Optional structured validation payload (e.g., Django form errors)
    errors: Optional[dict[str, list[FieldErrorItem]]] = None
    # Convenience: first message per field (flat)
    fields: Optional[dict[str, str]] = None


class OkOut(Schema):
    ok: bool
    message: Optional[str] = None


# ---------- Profile / Email ----------
class ProfileUpdateIn(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    vk_username: Optional[str] = None
    minecraft_nick: Optional[str] = None
    minecraft_has_license: Optional[bool] = None
    is_itmo_student: Optional[bool] = None
    itmo_isu: Optional[str] = None


class EmailStatusOut(Schema):
    email: Optional[str] = None
    verified: bool = False


class ChangeEmailIn(Schema):
    new_email: str


# ---------- Sessions ----------
class SessionRowOut(Schema):
    id: Optional[str]
    user_agent: Optional[str]
    ip: Optional[str]
    created: Optional[datetime]
    last_seen: Optional[datetime]
    expires: Optional[datetime]
    current: bool
    revoked: bool
    revoked_reason: Optional[str]
    revoked_at: Optional[datetime]


class SessionsOut(Schema):
    sessions: list[SessionRowOut]


class RevokeSessionsIn(Schema):
    ids: list[str] | None = None
    all_except_current: bool = False
    reason: str | None = None


class RevokeOut(Schema):
    ok: bool
    # bulk
    reason: Optional[str] = None
    current: Optional[str] = None
    revoked_ids: Optional[list[str]] = None
    skipped_ids: Optional[list[str]] = None
    count: Optional[int] = None
    # single
    id: Optional[str] = None
    revoked_reason: Optional[str] = None
    revoked_at: Optional[datetime] = None


# ---------- Auth / JWT ----------
class TokenPairOut(Schema):
    access: str
    refresh: str


class TokenRefreshIn(Schema):
    refresh: str


class TokenRefreshOut(Schema):
    refresh: str
    access: Optional[str] = None


class ChangePasswordIn(Schema):
    current_password: str
    new_password: str


class DeleteAccountIn(Schema):
    current_password: str


class ProfileOut(Schema):
    username: str
    email: str
    has_2fa: bool
    oauth_providers: List[str]
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    email_verified: bool = False
    profile_complete: bool = False
    account_active: bool = False
    registration_completed: bool = False
    profile_state: str = "basic"
    profile_tier: str = "basic"
    blocking_reasons: List[str]
    personalization_ui_enabled: bool = True
    personalization_interstitial_enabled: bool = True
    personalization_enforce_enabled: bool = False
    missing_fields: List[str]
    vk_username: Optional[str] = None
    minecraft_nick: Optional[str] = None
    minecraft_has_license: Optional[bool] = None
    is_itmo_student: Optional[bool] = None
    itmo_isu: Optional[str] = None


class AccountStatusOut(Schema):
    email_verified: bool = False
    profile_complete: bool = False
    account_active: bool = False
    registration_completed: bool = False
    profile_state: str = "basic"
    profile_tier: str = "basic"
    blocking_reasons: List[str]
    personalization_ui_enabled: bool = True
    personalization_interstitial_enabled: bool = True
    personalization_enforce_enabled: bool = False
    missing_fields: List[str]


class ProfileUpdateOut(Schema):
    ok: bool
    message: Optional[str] = None
    email_verified: bool = False
    profile_complete: bool = False
    account_active: bool = False
    registration_completed: bool = False
    profile_state: str = "basic"
    profile_tier: str = "basic"
    blocking_reasons: List[str]
    personalization_ui_enabled: bool = True
    personalization_interstitial_enabled: bool = True
    personalization_enforce_enabled: bool = False
    missing_fields: List[str]


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
    email: Optional[str] = None
    password: str


# ---------- OAuth linking ----------
class ProvidersOut(Schema):
    providers: list[dict]


class OAuthLinkOut(Schema):
    authorize_url: str
    method: str
