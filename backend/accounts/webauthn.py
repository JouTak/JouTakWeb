from __future__ import annotations

import base64
import binascii
import json
import re
from collections.abc import Collection, Mapping, MutableMapping
from dataclasses import dataclass
from hashlib import sha256
from typing import NoReturn

from allauth.mfa.webauthn.internal import auth as allauth_webauthn
from fido2.webauthn import UserVerificationRequirement

WEBAUTHN_CREATE = "webauthn.create"
WEBAUTHN_GET = "webauthn.get"
WEBAUTHN_CHALLENGE_SESSION_KEY = "_webauthn_challenge"
WEBAUTHN_SESSION_BINDING_KEY = "_webauthn_session_binding"
_KNOWN_CLIENT_DATA_TYPES = frozenset({WEBAUTHN_CREATE, WEBAUTHN_GET})
_BASE64URL_RE = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True, slots=True)
class WebAuthnClientDataError(ValueError):
    """Fail-closed WebAuthn boundary error safe to classify in logs."""

    reason_code: str

    def __str__(self) -> str:
        return "Invalid WebAuthn client data."


class WebAuthnStateError(ValueError):
    """The browser options and allauth verification state cannot be synced."""


@dataclass(frozen=True, slots=True)
class ValidatedWebAuthnClientData:
    ceremony_type: str
    challenge: bytes
    origin: str


def _reject(reason_code: str) -> NoReturn:
    raise WebAuthnClientDataError(reason_code)


def _decode_base64url(value: object) -> bytes:
    if not isinstance(value, str) or not value:
        _reject("missing_client_data")
    if not _BASE64URL_RE.fullmatch(value) or len(value) % 4 == 1:
        _reject("invalid_client_data_encoding")

    padding = "=" * (-len(value) % 4)
    try:
        return base64.b64decode(
            value + padding,
            altchars=b"-_",
            validate=True,
        )
    except (binascii.Error, ValueError):
        _reject("invalid_client_data_encoding")


def _parse_client_data(credential: object) -> Mapping[str, object]:
    if not isinstance(credential, Mapping):
        _reject("invalid_credential_shape")
    response = credential.get("response")
    if not isinstance(response, Mapping):
        _reject("invalid_credential_shape")

    raw_client_data = _decode_base64url(response.get("clientDataJSON"))
    try:
        client_data = json.loads(raw_client_data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        _reject("invalid_client_data_json")
    if not isinstance(client_data, Mapping):
        _reject("invalid_client_data_json")
    return client_data


def validate_webauthn_client_data(
    credential: object,
    *,
    expected_type: str,
    allowed_origins: Collection[str],
) -> ValidatedWebAuthnClientData:
    """Validate exact signed client-data policy before crypto verification.

    This is a fail-closed boundary check, not a replacement for WebAuthn
    cryptographic verification. Callers must pass the original, unmodified
    credential to django-allauth/FIDO2 after this function succeeds. The
    authenticator signature (or registration attestation) then binds the
    already-checked ``clientDataJSON`` bytes to the ceremony.
    """

    if expected_type not in _KNOWN_CLIENT_DATA_TYPES:
        raise ValueError("Unsupported WebAuthn client data type policy")

    if isinstance(allowed_origins, (str, bytes)):
        _reject("origin_policy_not_configured")
    try:
        origins = frozenset(allowed_origins)
    except TypeError:
        _reject("origin_policy_not_configured")
    if not origins or any(not isinstance(origin, str) for origin in origins):
        _reject("origin_policy_not_configured")

    client_data = _parse_client_data(credential)
    if client_data.get("type") != expected_type:
        _reject("unexpected_client_data_type")

    challenge = client_data.get("challenge")
    if not isinstance(challenge, str) or not challenge:
        _reject("missing_challenge")
    challenge_bytes = _decode_base64url(challenge)

    origin = client_data.get("origin")
    if not isinstance(origin, str) or origin not in origins:
        _reject("origin_not_allowed")

    cross_origin = client_data.get("crossOrigin", False)
    if not isinstance(cross_origin, bool):
        _reject("invalid_cross_origin_flag")
    if cross_origin:
        _reject("cross_origin_not_allowed")

    return ValidatedWebAuthnClientData(
        ceremony_type=expected_type,
        challenge=challenge_bytes,
        origin=origin,
    )


def require_webauthn_user_verification(
    session: MutableMapping[str, object],
    public_key: object,
) -> None:
    """Require UV in both browser options and allauth's signed state.

    Updating only ``userVerification`` in the response is cosmetic: FIDO2
    verifies the authenticator's UV flag against the server-side state saved
    by ``begin_authentication()``. Keep this private-allauth compatibility
    boundary in one project-owned module so callers cannot update only one
    side of the ceremony.
    """

    state = session.get(allauth_webauthn.STATE_SESSION_KEY)
    if not isinstance(state, dict) or not isinstance(public_key, dict):
        raise WebAuthnStateError("WebAuthn authentication state is missing.")

    required = UserVerificationRequirement.REQUIRED
    updated_state = dict(state)
    updated_state["user_verification"] = required
    session[allauth_webauthn.STATE_SESSION_KEY] = updated_state
    public_key["userVerification"] = required.value


def webauthn_challenge_digest(encoded_challenge: object) -> str:
    """Return a non-sensitive digest for a canonical base64url challenge."""

    return sha256(_decode_base64url(encoded_challenge)).hexdigest()


__all__ = [
    "WEBAUTHN_CREATE",
    "WEBAUTHN_CHALLENGE_SESSION_KEY",
    "WEBAUTHN_GET",
    "WEBAUTHN_SESSION_BINDING_KEY",
    "ValidatedWebAuthnClientData",
    "WebAuthnClientDataError",
    "WebAuthnStateError",
    "require_webauthn_user_verification",
    "validate_webauthn_client_data",
    "webauthn_challenge_digest",
]
