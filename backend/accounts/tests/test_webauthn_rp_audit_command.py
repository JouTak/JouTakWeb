from __future__ import annotations

import hashlib
from io import StringIO

from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from fido2 import cbor
from fido2.utils import websafe_encode


class AuditWebAuthnRpIdsCommandTests(TestCase):
    candidates = "joutak.ru,api.joutak.ru,admin.joutak.ru"

    def setUp(self) -> None:
        super().setUp()
        self.user = get_user_model().objects.create_user(
            username="webauthn_audit_user",
            password="StrongPass123!",
        )

    def _registration_credential(
        self,
        rp_id: str,
        marker: str,
    ) -> dict[str, object]:
        credential_id = f"synthetic-{marker}".encode()
        cose_public_key = cbor.encode(
            {
                1: 2,
                3: -7,
                -1: 1,
                -2: b"X" * 32,
                -3: b"Y" * 32,
            }
        )
        authenticator_data = b"".join(
            (
                hashlib.sha256(rp_id.encode()).digest(),
                bytes([0x41]),
                (0).to_bytes(4, "big"),
                bytes(16),
                len(credential_id).to_bytes(2, "big"),
                credential_id,
                cose_public_key,
            )
        )
        attestation_object = cbor.encode(
            {
                "fmt": "none",
                "attStmt": {},
                "authData": authenticator_data,
            }
        )
        client_data = (
            '{"type":"webauthn.create","challenge":"AA",'
            f'"origin":"https://{rp_id}"}}'
        ).encode()
        encoded_credential_id = websafe_encode(credential_id)
        return {
            "id": encoded_credential_id,
            "rawId": encoded_credential_id,
            "type": "public-key",
            "response": {
                "clientDataJSON": websafe_encode(client_data),
                "attestationObject": websafe_encode(attestation_object),
            },
            "clientExtensionResults": {"credProps": {"rk": True}},
        }

    def _create_webauthn(self, rp_id: str, marker: str) -> Authenticator:
        return Authenticator.objects.create(
            user=self.user,
            type=Authenticator.Type.WEBAUTHN,
            data={
                "name": f"Synthetic {marker}",
                "credential": self._registration_credential(rp_id, marker),
            },
        )

    def test_classifies_known_unknown_and_unparseable_credentials(
        self,
    ) -> None:
        for index, rp_id in enumerate(self.candidates.split(",")):
            self._create_webauthn(rp_id, f"known-{index}")
        self._create_webauthn("legacy.joutak.ru", "unknown")
        Authenticator.objects.create(
            user=self.user,
            type=Authenticator.Type.WEBAUTHN,
            data={"name": "Broken", "credential": {"invalid": True}},
        )
        Authenticator.objects.create(
            user=self.user,
            type=Authenticator.Type.TOTP,
            data={"secret": "not-part-of-the-webauthn-audit"},
        )

        stdout = StringIO()
        call_command(
            "audit_webauthn_rp_ids",
            "--candidates",
            self.candidates,
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("WebAuthn RP ID audit (read-only)", output)
        self.assertIn("rp_id=joutak.ru credentials=1", output)
        self.assertIn("rp_id=api.joutak.ru credentials=1", output)
        self.assertIn("rp_id=admin.joutak.ru credentials=1", output)
        self.assertIn("unknown=1", output)
        self.assertIn("unparseable=1", output)
        self.assertIn("total=5", output)
        self.assertNotIn("not-part-of-the-webauthn-audit", output)

    def test_verbose_output_contains_ids_but_not_credential_material(
        self,
    ) -> None:
        marker = "DO-NOT-PRINT-CREDENTIAL"
        authenticator = self._create_webauthn("joutak.ru", marker)
        encoded_credential_id = websafe_encode(f"synthetic-{marker}".encode())

        stdout = StringIO()
        call_command(
            "audit_webauthn_rp_ids",
            "--candidates",
            self.candidates,
            "--verbose",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn(f"authenticator_id={authenticator.pk}", output)
        self.assertIn(f"user_id={self.user.pk}", output)
        self.assertIn("classification=candidate", output)
        self.assertNotIn(marker, output)
        self.assertNotIn(encoded_credential_id, output)
        self.assertNotIn("clientDataJSON", output)
        self.assertNotIn("attestationObject", output)

    def test_command_does_not_modify_authenticator_rows(self) -> None:
        authenticator = self._create_webauthn("api.joutak.ru", "unchanged")
        original_data = authenticator.data

        with self.assertNumQueries(1):
            call_command(
                "audit_webauthn_rp_ids",
                "--candidates",
                self.candidates,
                stdout=StringIO(),
            )

        authenticator.refresh_from_db()
        self.assertEqual(authenticator.data, original_data)

    def test_rejects_malformed_or_duplicate_candidates(self) -> None:
        invalid_values = (
            "joutak.ru,",
            "https://joutak.ru",
            "*.joutak.ru",
            "joutak.ru:443",
            "user@joutak.ru",
            "JouTak.ru",
            "joutak.ru,joutak.ru",
        )
        for candidates in invalid_values:
            with self.subTest(candidates=candidates):
                with self.assertRaises(CommandError):
                    call_command(
                        "audit_webauthn_rp_ids",
                        "--candidates",
                        candidates,
                        stdout=StringIO(),
                    )
