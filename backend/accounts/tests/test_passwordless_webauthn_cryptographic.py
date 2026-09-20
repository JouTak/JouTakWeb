from __future__ import annotations

import json

from accounts.tests.base import APITestCase
from allauth.account.utils import user_pk_to_url_str
from allauth.headless import app_settings as headless_app_settings
from allauth.mfa.models import Authenticator
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from django.contrib.auth import SESSION_KEY, get_user_model
from django.core.cache import caches
from django.test import override_settings
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
ACCOUNT_ORIGIN = "https://joutak.ru"
API_HOST = "api.joutak.ru"
LOCMEM_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "passwordless-crypto-default",
    },
    "ratelimit": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "passwordless-crypto-ratelimit",
    },
    "webauthn_replay": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "passwordless-crypto-replay",
    },
}


def _client_data_json(*, challenge: str, ceremony_type: str) -> bytes:
    return json.dumps(
        {
            "type": ceremony_type,
            "challenge": challenge,
            "origin": ACCOUNT_ORIGIN,
            "crossOrigin": False,
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _registered_passkey(
    user,
) -> tuple[Authenticator, ec.EllipticCurvePrivateKey, bytes]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    credential_id = b"synthetic-passwordless-passkey"
    credential_data = AttestedCredentialData.create(
        Aaguid.NONE,
        credential_id,
        ES256.from_cryptography_key(private_key.public_key()),
    )
    auth_data = AuthenticatorData.create(
        sha256(RP_ID.encode("ascii")),
        AuthenticatorData.FLAG.UP
        | AuthenticatorData.FLAG.UV
        | AuthenticatorData.FLAG.AT,
        0,
        credential_data,
    )
    client_data = _client_data_json(
        challenge=websafe_encode(b"synthetic-registration-challenge"),
        ceremony_type="webauthn.create",
    )
    registration = {
        "id": websafe_encode(credential_id),
        "rawId": websafe_encode(credential_id),
        "type": "public-key",
        "response": {
            "clientDataJSON": websafe_encode(client_data),
            "attestationObject": websafe_encode(
                bytes(AttestationObject.create("none", auth_data, {}))
            ),
        },
        "clientExtensionResults": {"credProps": {"rk": True}},
    }
    authenticator = Authenticator.objects.create(
        user=user,
        type=Authenticator.Type.WEBAUTHN,
        data={
            "name": "Synthetic passwordless passkey",
            "credential": registration,
        },
    )
    return authenticator, private_key, credential_id


def _signed_assertion(
    *,
    user,
    challenge: str,
    private_key: ec.EllipticCurvePrivateKey,
    credential_id: bytes,
    user_verified: bool,
) -> dict[str, object]:
    client_data = _client_data_json(
        challenge=challenge,
        ceremony_type="webauthn.get",
    )
    flags = AuthenticatorData.FLAG.UP
    if user_verified:
        flags |= AuthenticatorData.FLAG.UV
    authenticator_data = AuthenticatorData.create(
        sha256(RP_ID.encode("ascii")),
        flags,
        1,
    )
    signature = private_key.sign(
        bytes(authenticator_data) + sha256(client_data),
        ec.ECDSA(hashes.SHA256()),
    )
    encoded_id = websafe_encode(credential_id)
    user_handle = websafe_encode(user_pk_to_url_str(user).encode("utf-8"))
    return {
        "id": encoded_id,
        "rawId": encoded_id,
        "type": "public-key",
        "response": {
            "clientDataJSON": websafe_encode(client_data),
            "authenticatorData": websafe_encode(bytes(authenticator_data)),
            "signature": websafe_encode(signature),
            "userHandle": user_handle,
        },
        "clientExtensionResults": {},
    }


@override_settings(
    ACCOUNT_RATE_LIMITS=False,
    ALLOWED_HOSTS=("joutak.ru", API_HOST),
    CACHES=LOCMEM_CACHE,
    DJANGO_ADMIN_HOSTS=(),
    DJANGO_API_HOSTS=("joutak.ru", API_HOST),
    MFA_PASSKEY_LOGIN_ENABLED=True,
    MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN=False,
    WEBAUTHN_RP_ID=RP_ID,
    WEBAUTHN_RP_NAME="JouTak",
    WEBAUTHN_ACCOUNT_ORIGINS=(ACCOUNT_ORIGIN,),
    WEBAUTHN_ADMIN_ORIGINS=("https://admin.joutak.ru",),
    WEBAUTHN_ALLOWED_ORIGINS=(
        ACCOUNT_ORIGIN,
        "https://admin.joutak.ru",
    ),
    WEBAUTHN_CHALLENGE_TTL_SECONDS=300,
)
class PasswordlessWebAuthnCryptographicTests(APITestCase):
    def setUp(self) -> None:
        super().setUp()
        for backend in caches.all():
            backend.clear()
        self.user = User.objects.create_user(
            username="passwordless_crypto",
            email="passwordless-crypto@example.com",
            password="StrongPass123!",
        )
        (
            self.authenticator,
            self.private_key,
            self.credential_id,
        ) = _registered_passkey(self.user)

    def _options(self) -> tuple[str, str]:
        response = self.client.get(
            self.headless("/auth/webauthn/login"),
            HTTP_HOST=API_HOST,
        )
        self.assertEqual(response.status_code, 200, response.content)
        public_key = response.json()["data"]["request_options"]["publicKey"]
        self.assertEqual(public_key["rpId"], RP_ID)
        self.assertEqual(public_key["userVerification"], "required")
        token = self.session_token(response)
        self.assertTrue(token)
        session = headless_app_settings.TOKEN_STRATEGY.lookup_session(token)
        self.assertEqual(
            session["mfa.webauthn.state"]["user_verification"],
            "required",
        )
        return token or "", public_key["challenge"]

    def _complete(self, *, user_verified: bool):
        token, challenge = self._options()
        assertion = _signed_assertion(
            user=self.user,
            challenge=challenge,
            private_key=self.private_key,
            credential_id=self.credential_id,
            user_verified=user_verified,
        )
        response = self.headless_post_json(
            "/auth/webauthn/login",
            {"credential": assertion},
            **self.auth_headers(token),
            HTTP_HOST=API_HOST,
            HTTP_ORIGIN=ACCOUNT_ORIGIN,
        )
        return token, response

    def test_uv_assertion_creates_passwordless_session(self):
        _old_token, response = self._complete(user_verified=True)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["meta"]["is_authenticated"])
        token = self.session_token(response)
        self.assertTrue(token)
        session = headless_app_settings.TOKEN_STRATEGY.lookup_session(token)
        self.assertEqual(session[SESSION_KEY], str(self.user.pk))
        self.authenticator.refresh_from_db()
        self.assertIsNotNone(self.authenticator.last_used_at)

    def test_non_uv_assertion_is_rejected_without_session_or_usage(self):
        token, response = self._complete(user_verified=False)

        self.assertEqual(response.status_code, 400, response.content)
        session = headless_app_settings.TOKEN_STRATEGY.lookup_session(token)
        self.assertNotIn(SESSION_KEY, session)
        self.authenticator.refresh_from_db()
        self.assertIsNone(self.authenticator.last_used_at)
