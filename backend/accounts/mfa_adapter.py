from __future__ import annotations

import base64
import hashlib
from functools import cached_property

from allauth.mfa.adapter import DefaultMFAAdapter
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings


class EncryptedMFAAdapter(DefaultMFAAdapter):
    @cached_property
    def _fernet(self) -> MultiFernet:
        instances = [Fernet(self._derive_key(raw)) for raw in self._raw_keys()]
        return MultiFernet(instances)

    def _raw_keys(self) -> tuple[str, ...]:
        configured = tuple(getattr(settings, "MFA_ENCRYPTION_KEYS", ()))
        secret_key = getattr(settings, "SECRET_KEY", "")
        include_legacy_secret = getattr(
            settings,
            "MFA_ENCRYPTION_INCLUDE_LEGACY_SECRET_KEY",
            True,
        )
        combined: list[str] = []
        for raw in configured:
            if raw and raw not in combined:
                combined.append(raw)
        if include_legacy_secret and secret_key and secret_key not in combined:
            combined.append(secret_key)
        if combined:
            return tuple(combined)
        raise RuntimeError("No key material is available for MFA encryption")

    def _derive_key(self, raw: str) -> bytes:
        digest = hashlib.sha256(raw.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    def _prefix(self) -> str:
        return getattr(settings, "MFA_ENCRYPTION_PREFIX", "fernet:")

    def encrypt(self, text: str) -> str:
        if not text:
            return text
        encrypted = self._fernet.encrypt(text.encode("utf-8")).decode("ascii")
        return f"{self._prefix()}{encrypted}"

    def decrypt(self, encrypted_text: str) -> str:
        if not encrypted_text:
            return encrypted_text
        prefix = self._prefix()
        if not encrypted_text.startswith(prefix):
            return encrypted_text
        token = encrypted_text[len(prefix) :].encode("ascii")
        try:
            return self._fernet.decrypt(token).decode("utf-8")
        except InvalidToken as exc:
            raise RuntimeError("Failed to decrypt MFA secret") from exc
