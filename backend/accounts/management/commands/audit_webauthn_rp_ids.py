from __future__ import annotations

import hashlib
import re
from argparse import ArgumentParser

from allauth.mfa.models import Authenticator
from django.core.management.base import BaseCommand, CommandError
from fido2.webauthn import RegistrationResponse

_RP_ID_PATTERN = re.compile(
    r"^(?:localhost|(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)"
    r"(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))+)$"
)


class Command(BaseCommand):
    help = (
        "Classify stored WebAuthn credentials by the SHA-256 hash of "
        "candidate RP IDs without modifying authenticator data."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--candidates",
            required=True,
            help=(
                "Comma-separated exact RP IDs to compare, for example "
                "joutak.ru,api.joutak.ru,admin.joutak.ru."
            ),
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help=(
                "Print internal user/authenticator IDs and classification; "
                "credential material is never printed."
            ),
        )

    def handle(self, *args, **options) -> None:
        candidates = self._parse_candidates(options["candidates"])
        candidate_by_hash = {
            hashlib.sha256(candidate.encode()).digest(): candidate
            for candidate in candidates
        }
        counts = dict.fromkeys(candidates, 0)
        unknown = 0
        unparseable = 0
        total = 0
        verbose = bool(options["verbose"])

        authenticators = (
            Authenticator.objects.filter(type=Authenticator.Type.WEBAUTHN)
            .only("id", "user_id", "data")
            .order_by("id")
        )
        for authenticator in authenticators.iterator(chunk_size=500):
            total += 1
            # Malformed persisted payloads are audit results, not fatal
            # command errors.
            try:
                rp_id_hash = self._extract_rp_id_hash(authenticator.data)
            except Exception:
                unparseable += 1
                self._write_verbose(
                    verbose,
                    authenticator,
                    classification="unparseable",
                )
                continue

            candidate = candidate_by_hash.get(rp_id_hash)
            if candidate is None:
                unknown += 1
                self._write_verbose(
                    verbose,
                    authenticator,
                    classification="unknown",
                )
                continue

            counts[candidate] += 1
            self._write_verbose(
                verbose,
                authenticator,
                classification="candidate",
                rp_id=candidate,
            )

        self.stdout.write("WebAuthn RP ID audit (read-only)")
        for candidate, count in counts.items():
            self.stdout.write(f"rp_id={candidate} credentials={count}")
        self.stdout.write(f"unknown={unknown}")
        self.stdout.write(f"unparseable={unparseable}")
        self.stdout.write(f"total={total}")

    @staticmethod
    def _parse_candidates(raw_candidates: str) -> tuple[str, ...]:
        raw_parts = raw_candidates.split(",")
        candidates = tuple(part.strip() for part in raw_parts)
        if not candidates or any(not candidate for candidate in candidates):
            raise CommandError(
                "--candidates must contain comma-separated non-empty RP IDs"
            )

        invalid = [
            candidate
            for candidate in candidates
            if not _RP_ID_PATTERN.fullmatch(candidate)
        ]
        if invalid:
            raise CommandError(
                "--candidates values must be lowercase hostnames without "
                "scheme, port, path, credentials, wildcard, or whitespace"
            )
        if len(set(candidates)) != len(candidates):
            raise CommandError(
                "--candidates must not contain duplicate RP IDs"
            )
        return candidates

    @staticmethod
    def _extract_rp_id_hash(data: object) -> bytes:
        if not isinstance(data, dict):
            raise ValueError("authenticator data is not an object")
        credential = data.get("credential")
        if not isinstance(credential, dict):
            raise ValueError("registration credential is missing")

        registration = RegistrationResponse.from_dict(credential)
        rp_id_hash = (
            registration.response.attestation_object.auth_data.rp_id_hash
        )
        value = bytes(rp_id_hash)
        if len(value) != hashlib.sha256().digest_size:
            raise ValueError("RP ID hash has an unexpected length")
        return value

    def _write_verbose(
        self,
        verbose: bool,
        authenticator: Authenticator,
        *,
        classification: str,
        rp_id: str | None = None,
    ) -> None:
        if not verbose:
            return
        fields = [
            f"authenticator_id={authenticator.pk}",
            f"user_id={authenticator.user_id}",
            f"classification={classification}",
        ]
        if rp_id is not None:
            fields.append(f"rp_id={rp_id}")
        self.stdout.write(" ".join(fields))
