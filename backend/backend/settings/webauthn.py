from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

_RP_ID_PATTERN = re.compile(
    r"^(?:localhost|(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))+)$"
)


def parse_webauthn_origins(raw_value: str) -> tuple[str, ...]:
    """Split an origin list without treating URL fragments as comments."""

    return tuple(part.strip() for part in raw_value.split(","))


def validate_webauthn_configuration(
    *,
    rp_id: str,
    rp_name: str,
    account_origins: Iterable[str],
    admin_origins: Iterable[str],
    allowed_origins: Iterable[str] | None,
    require_https: bool,
    allow_ports: bool,
) -> tuple[str, str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Validate and normalize the project-owned WebAuthn trust boundary."""
    normalized_rp_id = (rp_id or "").strip().lower()
    if rp_id != normalized_rp_id or not _RP_ID_PATTERN.fullmatch(
        normalized_rp_id
    ):
        raise ImproperlyConfigured(
            "WEBAUTHN_RP_ID must be a lowercase hostname without a scheme, "
            "port, path, wildcard, or whitespace."
        )

    normalized_rp_name = (rp_name or "").strip()
    if not normalized_rp_name:
        raise ImproperlyConfigured("WEBAUTHN_RP_NAME must not be empty.")

    account = _validate_origins(
        account_origins,
        rp_id=normalized_rp_id,
        setting_name="WEBAUTHN_ACCOUNT_ORIGINS",
        require_https=require_https,
        allow_ports=allow_ports,
    )
    admin = _validate_origins(
        admin_origins,
        rp_id=normalized_rp_id,
        setting_name="WEBAUTHN_ADMIN_ORIGINS",
        require_https=require_https,
        allow_ports=allow_ports,
    )
    overlap = sorted(set(account) & set(admin))
    if overlap:
        raise ImproperlyConfigured(
            "WebAuthn account and admin origins must be distinct; overlap: "
            f"{overlap}."
        )

    allowed = tuple(dict.fromkeys((*account, *admin)))
    if allowed_origins is not None:
        configured_allowed = _validate_origins(
            allowed_origins,
            rp_id=normalized_rp_id,
            setting_name="WEBAUTHN_ALLOWED_ORIGINS",
            require_https=require_https,
            allow_ports=allow_ports,
        )
        if set(configured_allowed) != set(allowed):
            raise ImproperlyConfigured(
                "WEBAUTHN_ALLOWED_ORIGINS must equal the union of account "
                "and admin origins."
            )
        allowed = configured_allowed
    return normalized_rp_id, normalized_rp_name, account, admin, allowed


def _validate_origins(
    origins: Iterable[str],
    *,
    rp_id: str,
    setting_name: str,
    require_https: bool,
    allow_ports: bool,
) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw_origin in origins:
        origin = (raw_origin or "").strip()
        if not origin or origin == "*" or "*" in origin:
            raise ImproperlyConfigured(
                f"{setting_name} must contain exact origins and no wildcard."
            )
        parsed = urlsplit(origin)
        try:
            port = parsed.port
        except ValueError as exc:
            raise ImproperlyConfigured(
                f"{setting_name} contains an invalid port."
            ) from exc
        hostname = parsed.hostname
        if (
            parsed.scheme not in {"http", "https"}
            or not hostname
            or parsed.username is not None
            or parsed.password is not None
            or origin != origin.lower()
        ):
            raise ImproperlyConfigured(
                f"{setting_name} contains an invalid exact origin."
            )

        # ``urlsplit()`` does not retain whether empty query/fragment
        # delimiters were present, and treats a trailing ``:`` as a netloc
        # with no port. Compare against the one canonical lexical form so
        # those malformed values cannot enter the signed-origin allowlist.
        canonical_origin = f"{parsed.scheme}://{hostname}"
        if port is not None:
            canonical_origin = f"{canonical_origin}:{port}"
        if origin != canonical_origin:
            raise ImproperlyConfigured(
                f"{setting_name} contains an invalid exact origin."
            )
        if require_https and parsed.scheme != "https":
            raise ImproperlyConfigured(
                f"{setting_name} must contain HTTPS origins in production."
            )
        if port is not None and not allow_ports:
            raise ImproperlyConfigured(
                f"{setting_name} must not contain an explicit port in "
                "production."
            )
        host = hostname.lower()
        if host != rp_id and not host.endswith(f".{rp_id}"):
            raise ImproperlyConfigured(
                f"{setting_name} contains a host outside WEBAUTHN_RP_ID."
            )
        if origin in normalized:
            continue
        normalized.append(origin)

    if not normalized:
        raise ImproperlyConfigured(f"{setting_name} must not be empty.")
    return tuple(normalized)
