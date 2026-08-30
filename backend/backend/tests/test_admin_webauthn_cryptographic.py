from __future__ import annotations

import json

from accounts.services.admin_mfa import (
    SESSION_KEY_ADMIN_MFA_ASSURANCE,
    SESSION_KEY_ADMIN_MFA_PENDING,
)
from allauth.account.internal.flows.login import (
    AUTHENTICATION_METHODS_SESSION_KEY,
)
from allauth.mfa.models import Authenticator
from allauth.mfa.webauthn.internal import auth as allauth_webauthn
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from django.contrib.auth import SESSION_KEY, get_user_model
from django.core.cache import caches
from django.test import TestCase, override_settings
from fido2.cose import ES256
from fido2.utils import sha256, websafe_encode
from fido2.webauthn import (
    Aaguid,
    AttestationObject,
    AttestedCredentialData,
    AuthenticatorData,
)

User = get_user_model()

RP_ID = "joutak.ru"
ADMIN_ORIGIN = "https://admin.joutak.ru"
ADMIN_HOST = "admin.joutak.ru"
PASSWORD = "StrongPass123!"
LOCMEM_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "admin-webauthn-cryptographic-tests-default",
    },
    "ratelimit": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "admin-webauthn-cryptographic-tests-ratelimit",
    },
    "webauthn_replay": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "admin-webauthn-cryptographic-tests-replay",
    },
}


def _client_data_json(*, challenge: str, ceremony_type: str) -> bytes:
    return json.dumps(
        {
            "type": ceremony_type,
            "challenge": challenge,
            "origin": ADMIN_ORIGIN,
            "crossOrigin": False,
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _registered_webauthn_authenticator(
    user,
) -> tuple[Authenticator, ec.EllipticCurvePrivateKey, bytes]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    credential_id = b"synthetic-admin-webauthn-credential"
    credential_data = AttestedCredentialData.create(
        Aaguid.NONE,
        credential_id,
        ES256.from_cryptography_key(private_key.public_key()),
    )
    registration_auth_data = AuthenticatorData.create(
        sha256(RP_ID.encode("ascii")),
        AuthenticatorData.FLAG.UP
        | AuthenticatorData.FLAG.UV
        | AuthenticatorData.FLAG.AT,
        0,
        credential_data,
    )
    registration_client_data = _client_data_json(
        challenge=websafe_encode(b"synthetic-registration-challenge"),
        ceremony_type="webauthn.create",
    )
    attestation_object = AttestationObject.create(
        "none",
        registration_auth_data,
        {},
    )
    registration = {
        "id": websafe_encode(credential_id),
        "rawId": websafe_encode(credential_id),
        "type": "public-key",
        "response": {
            "clientDataJSON": websafe_encode(registration_client_data),
            "attestationObject": websafe_encode(bytes(attestation_object)),
        },
        "clientExtensionResults": {},
    }
    authenticator = Authenticator.objects.create(
        user=user,
        type=Authenticator.Type.WEBAUTHN,
        data={
            "name": "Synthetic admin passkey",
            "credential": registration,
        },
    )
    return authenticator, private_key, credential_id


def _signed_assertion(
    *,
    challenge: str,
    private_key: ec.EllipticCurvePrivateKey,
    credential_id: bytes,
    user_verified: bool,
    rp_id: str = RP_ID,
    signing_key: ec.EllipticCurvePrivateKey | None = None,
) -> dict[str, object]:
    client_data = _client_data_json(
        challenge=challenge,
        ceremony_type="webauthn.get",
    )
    flags = AuthenticatorData.FLAG.UP
    if user_verified:
        flags |= AuthenticatorData.FLAG.UV
    authenticator_data = AuthenticatorData.create(
        sha256(rp_id.encode("ascii")),
        flags,
        1,
    )
    signature = (signing_key or private_key).sign(
        bytes(authenticator_data) + sha256(client_data),
        ec.ECDSA(hashes.SHA256()),
    )
    encoded_credential_id = websafe_encode(credential_id)
    return {
        "id": encoded_credential_id,
        "rawId": encoded_credential_id,
        "type": "public-key",
        "response": {
            "clientDataJSON": websafe_encode(client_data),
            "authenticatorData": websafe_encode(bytes(authenticator_data)),
            "signature": websafe_encode(signature),
        },
        "clientExtensionResults": {},
    }


@override_settings(
    ACCOUNT_RATE_LIMITS=False,
    ALLOWED_HOSTS=(ADMIN_HOST,),
    CACHES=LOCMEM_CACHE,
    DJANGO_ADMIN_HOSTS=(ADMIN_HOST,),
    DJANGO_API_HOSTS=(),
    MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN=False,
    WEBAUTHN_RP_ID=RP_ID,
    WEBAUTHN_RP_NAME="JouTak",
    WEBAUTHN_ACCOUNT_ORIGINS=("https://joutak.ru",),
    WEBAUTHN_ADMIN_ORIGINS=(ADMIN_ORIGIN,),
    WEBAUTHN_ALLOWED_ORIGINS=("https://joutak.ru", ADMIN_ORIGIN),
    WEBAUTHN_CHALLENGE_TTL_SECONDS=300,
    ADMIN_MFA_PENDING_TTL_SECONDS=300,
    ADMIN_MFA_ASSURANCE_TTL_SECONDS=28800,
)
class AdminWebAuthnCryptographicFlowTests(TestCase):
    def setUp(self) -> None:
        for backend in caches.all():
            backend.clear()
        self.user = User.objects.create_user(
            username="cryptographic_admin",
            email="cryptographic-admin@example.com",
            password=PASSWORD,
            is_staff=True,
        )
        (
            self.authenticator,
            self.private_key,
            self.credential_id,
        ) = _registered_webauthn_authenticator(self.user)

    def _begin_password_and_webauthn(self) -> tuple[str, str]:
        session = self.client.session
        session["pre_login_marker"] = True
        session.save()
        original_session_key = session.session_key

        password_response = self.client.post(
            "/admin/login/",
            {
                "username": self.user.username,
                "password": PASSWORD,
                "next": "/admin/",
            },
            HTTP_HOST=ADMIN_HOST,
            HTTP_ORIGIN=ADMIN_ORIGIN,
            secure=True,
        )
        self.assertEqual(
            password_response.status_code,
            302,
            password_response.content,
        )
        self.assertEqual(
            password_response.headers["Location"],
            "/admin/mfa-verify/",
        )
        pending_session_key = self.client.session.session_key
        self.assertNotEqual(pending_session_key, original_session_key)
        self.assertIn(SESSION_KEY_ADMIN_MFA_PENDING, self.client.session)
        self.assertNotIn(SESSION_KEY, self.client.session)

        options_response = self.client.get(
            "/admin/mfa-verify/webauthn-options/",
            HTTP_HOST=ADMIN_HOST,
            secure=True,
        )
        self.assertEqual(
            options_response.status_code,
            200,
            options_response.content,
        )
        public_key = options_response.json()["publicKey"]
        self.assertEqual(public_key["rpId"], RP_ID)
        self.assertEqual(public_key["userVerification"], "required")
        self.assertIn("no-store", options_response.headers["Cache-Control"])
        return pending_session_key, public_key["challenge"]

    def _assert_assertion_rejected_without_admin_session(
        self,
        assertion: dict[str, object],
        *,
        pending_session_key: str,
    ) -> None:
        completion = self.client.post(
            "/admin/mfa-verify/webauthn-complete/",
            data=json.dumps(assertion),
            content_type="application/json",
            HTTP_HOST=ADMIN_HOST,
            HTTP_ORIGIN=ADMIN_ORIGIN,
            secure=True,
        )

        self.assertEqual(completion.status_code, 400, completion.content)
        self.assertEqual(completion.json(), {"error": "Verification failed"})
        failed_session = self.client.session
        self.assertEqual(failed_session.session_key, pending_session_key)
        self.assertNotIn(SESSION_KEY, failed_session)
        self.assertNotIn(SESSION_KEY_ADMIN_MFA_ASSURANCE, failed_session)
        self.assertIn(SESSION_KEY_ADMIN_MFA_PENDING, failed_session)
        records = failed_session.get(AUTHENTICATION_METHODS_SESSION_KEY, [])
        self.assertFalse(
            any(record.get("method") == "mfa" for record in records)
        )
        self.authenticator.refresh_from_db()
        self.assertIsNone(self.authenticator.last_used_at)

    def test_password_and_uv_assertion_create_assured_admin_session(self):
        pending_session_key, challenge = self._begin_password_and_webauthn()
        assertion = _signed_assertion(
            challenge=challenge,
            private_key=self.private_key,
            credential_id=self.credential_id,
            user_verified=True,
        )

        completion = self.client.post(
            "/admin/mfa-verify/webauthn-complete/",
            data=json.dumps(assertion),
            content_type="application/json",
            HTTP_HOST=ADMIN_HOST,
            HTTP_ORIGIN=ADMIN_ORIGIN,
            secure=True,
        )

        self.assertEqual(completion.status_code, 200, completion.content)
        self.assertEqual(
            completion.json(),
            {"ok": True, "redirect": "/admin/"},
        )
        final_session = self.client.session
        self.assertNotEqual(final_session.session_key, pending_session_key)
        self.assertEqual(final_session[SESSION_KEY], str(self.user.pk))
        self.assertNotIn(SESSION_KEY_ADMIN_MFA_PENDING, final_session)
        self.assertNotIn(allauth_webauthn.STATE_SESSION_KEY, final_session)
        assurance = final_session[SESSION_KEY_ADMIN_MFA_ASSURANCE]
        self.assertEqual(assurance["user_pk"], str(self.user.pk))
        self.assertEqual(assurance["method"], "webauthn")

        authentication_records = final_session[
            AUTHENTICATION_METHODS_SESSION_KEY
        ]
        self.assertTrue(
            any(
                record.get("method") == "mfa"
                and record.get("type") == Authenticator.Type.WEBAUTHN
                and record.get("id") == self.authenticator.pk
                for record in authentication_records
            )
        )
        self.authenticator.refresh_from_db()
        self.assertIsNotNone(self.authenticator.last_used_at)

        admin_response = self.client.get(
            "/admin/",
            HTTP_HOST=ADMIN_HOST,
            secure=True,
        )
        self.assertEqual(admin_response.status_code, 200)

    def test_assertion_without_uv_is_rejected_without_admin_session(self):
        pending_session_key, challenge = self._begin_password_and_webauthn()
        assertion = _signed_assertion(
            challenge=challenge,
            private_key=self.private_key,
            credential_id=self.credential_id,
            user_verified=False,
        )

        self._assert_assertion_rejected_without_admin_session(
            assertion,
            pending_session_key=pending_session_key,
        )

    def test_assertion_with_wrong_rp_hash_is_rejected(self):
        pending_session_key, challenge = self._begin_password_and_webauthn()
        assertion = _signed_assertion(
            challenge=challenge,
            private_key=self.private_key,
            credential_id=self.credential_id,
            user_verified=True,
            rp_id="admin.joutak.ru",
        )

        self._assert_assertion_rejected_without_admin_session(
            assertion,
            pending_session_key=pending_session_key,
        )

    def test_assertion_with_invalid_signature_is_rejected(self):
        pending_session_key, challenge = self._begin_password_and_webauthn()
        assertion = _signed_assertion(
            challenge=challenge,
            private_key=self.private_key,
            credential_id=self.credential_id,
            user_verified=True,
            signing_key=ec.generate_private_key(ec.SECP256R1()),
        )

        self._assert_assertion_rejected_without_admin_session(
            assertion,
            pending_session_key=pending_session_key,
        )
