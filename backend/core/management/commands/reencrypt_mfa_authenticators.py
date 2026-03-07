from __future__ import annotations

from allauth.mfa.adapter import get_adapter as get_mfa_adapter
from allauth.mfa.models import Authenticator
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = (
        "Encrypt legacy plaintext MFA secrets using the configured MFA "
        "adapter."
    )

    def _encrypt_if_needed(self, adapter, value: str) -> tuple[str, bool]:
        if not value:
            return value, False
        decrypted = adapter.decrypt(value)
        encrypted = adapter.encrypt(decrypted)
        return encrypted, encrypted != value

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        adapter = get_mfa_adapter()
        updated = 0
        query = Authenticator.objects.select_for_update()
        for authenticator in query.iterator():
            data = dict(authenticator.data or {})
            changed = False

            for key in ("secret", "seed"):
                value = data.get(key)
                if isinstance(value, str):
                    data[key], key_changed = self._encrypt_if_needed(
                        adapter, value
                    )
                    changed = changed or key_changed

            migrated_codes = data.get("migrated_codes")
            if isinstance(migrated_codes, list):
                next_codes: list[str] = []
                codes_changed = False
                for code in migrated_codes:
                    if not isinstance(code, str):
                        next_codes.append(code)
                        continue
                    next_code, key_changed = self._encrypt_if_needed(
                        adapter, code
                    )
                    next_codes.append(next_code)
                    codes_changed = codes_changed or key_changed
                if codes_changed:
                    data["migrated_codes"] = next_codes
                    changed = True

            if not changed:
                continue
            authenticator.data = data
            authenticator.save(update_fields=["data"])
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"reencrypt_mfa_authenticators completed: updated={updated}"
            )
        )
