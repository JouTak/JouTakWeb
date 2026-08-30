from __future__ import annotations

import base64
import copy
import json
import time
from types import SimpleNamespace
from unittest.mock import patch

from accounts.mfa_adapter import EncryptedMFAAdapter
from accounts.middleware import (
    WEBAUTHN_COMPLETION_POLICIES,
    WEBAUTHN_OPTIONS_POLICIES,
    WebAuthnOriginValidationMiddleware,
)
from accounts.services.admin_mfa import SESSION_KEY_ADMIN_MFA_PENDING
from accounts.tests.base import APITestCase
from accounts.webauthn import (
    WEBAUTHN_CHALLENGE_SESSION_KEY,
    WEBAUTHN_CREATE,
    WEBAUTHN_GET,
    WEBAUTHN_SESSION_BINDING_KEY,
    WebAuthnClientDataError,
    validate_webauthn_client_data,
)
from allauth.account.models import EmailAddress
from allauth.core import context as allauth_context
from allauth.headless import app_settings as headless_app_settings
from allauth.mfa.models import Authenticator
from allauth.mfa.webauthn.internal import auth as allauth_webauthn
from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.sessions.backends.signed_cookies import (
    SessionStore as CookieSessionStore,
)
from django.core.cache import caches
from django.http import JsonResponse
from django.test import (
    RequestFactory,
    SimpleTestCase,
    TestCase,
    override_settings,
)
from django.urls import resolve

ACCOUNT_ORIGIN = "https://joutak.ru"
ADMIN_ORIGIN = "https://admin.joutak.ru"
API_ORIGIN = "https://api.joutak.ru"
CHALLENGE = "dGVzdC1jaGFsbGVuZ2U"
OTHER_CHALLENGE = "YW5vdGhlci1jaGFsbGVuZ2U"
LOCMEM_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "webauthn-boundary-tests-default",
    },
    "ratelimit": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "webauthn-boundary-tests-ratelimit",
    },
    "webauthn_replay": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "webauthn-boundary-tests-replay",
    },
}


def _client_data_json(
    *,
    origin: str = ACCOUNT_ORIGIN,
    ceremony_type: str = WEBAUTHN_GET,
    challenge: str = CHALLENGE,
    cross_origin: object = False,
) -> str:
    payload = {
        "type": ceremony_type,
        "challenge": challenge,
        "origin": origin,
        "crossOrigin": cross_origin,
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    return encoded.rstrip(b"=").decode("ascii")


def _credential(
    *,
    origin: str = ACCOUNT_ORIGIN,
    ceremony_type: str = WEBAUTHN_GET,
    challenge: str = CHALLENGE,
    cross_origin: object = False,
) -> dict[str, object]:
    return {
        "id": "credential-id",
        "rawId": "credential-id",
        "type": "public-key",
        "response": {
            "clientDataJSON": _client_data_json(
                origin=origin,
                ceremony_type=ceremony_type,
                challenge=challenge,
                cross_origin=cross_origin,
            )
        },
    }


class WebAuthnClientDataValidationTests(SimpleTestCase):
    def test_accepts_exact_origin_and_expected_type(self) -> None:
        validated = validate_webauthn_client_data(
            _credential(),
            expected_type=WEBAUTHN_GET,
            allowed_origins=(ACCOUNT_ORIGIN,),
        )
        self.assertEqual(validated.challenge, b"test-challenge")
        self.assertEqual(validated.origin, ACCOUNT_ORIGIN)

    def test_rejects_non_exact_origins(self) -> None:
        rejected = (
            ADMIN_ORIGIN,
            API_ORIGIN,
            "https://evil.joutak.ru",
            "https://www.joutak.ru",
            "https://joutak.ru.evil.example",
            "http://joutak.ru",
            "https://joutak.ru:444",
            "https://JOUTAK.RU",
        )
        for origin in rejected:
            with self.subTest(origin=origin):
                with self.assertRaises(WebAuthnClientDataError) as raised:
                    validate_webauthn_client_data(
                        _credential(origin=origin),
                        expected_type=WEBAUTHN_GET,
                        allowed_origins=(ACCOUNT_ORIGIN,),
                    )
                self.assertEqual(
                    raised.exception.reason_code, "origin_not_allowed"
                )

    def test_rejects_wrong_ceremony_type(self) -> None:
        with self.assertRaises(WebAuthnClientDataError) as raised:
            validate_webauthn_client_data(
                _credential(ceremony_type=WEBAUTHN_CREATE),
                expected_type=WEBAUTHN_GET,
                allowed_origins=(ACCOUNT_ORIGIN,),
            )
        self.assertEqual(
            raised.exception.reason_code,
            "unexpected_client_data_type",
        )

    def test_rejects_cross_origin_ceremony(self) -> None:
        with self.assertRaises(WebAuthnClientDataError) as raised:
            validate_webauthn_client_data(
                _credential(cross_origin=True),
                expected_type=WEBAUTHN_GET,
                allowed_origins=(ACCOUNT_ORIGIN,),
            )
        self.assertEqual(
            raised.exception.reason_code,
            "cross_origin_not_allowed",
        )

    def test_rejects_missing_malformed_or_non_json_client_data(self) -> None:
        cases = (
            {},
            {"response": {}},
            {"response": {"clientDataJSON": "!!!"}},
            {
                "response": {
                    "clientDataJSON": base64.urlsafe_b64encode(b"not-json")
                    .rstrip(b"=")
                    .decode("ascii")
                }
            },
        )
        for credential in cases:
            with self.subTest(credential=credential):
                with self.assertRaises(WebAuthnClientDataError):
                    validate_webauthn_client_data(
                        credential,
                        expected_type=WEBAUTHN_GET,
                        allowed_origins=(ACCOUNT_ORIGIN,),
                    )

    def test_rejects_empty_origin_policy(self) -> None:
        with self.assertRaises(WebAuthnClientDataError) as raised:
            validate_webauthn_client_data(
                _credential(),
                expected_type=WEBAUTHN_GET,
                allowed_origins=(),
            )
        self.assertEqual(
            raised.exception.reason_code,
            "origin_policy_not_configured",
        )

    def test_rejects_unknown_expected_type_as_programming_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported WebAuthn"):
            validate_webauthn_client_data(
                _credential(),
                expected_type="unknown",
                allowed_origins=(ACCOUNT_ORIGIN,),
            )


@override_settings(
    ALLOWED_HOSTS=["api.joutak.ru", "admin.joutak.ru"],
    WEBAUTHN_ACCOUNT_ORIGINS=(ACCOUNT_ORIGIN,),
    WEBAUTHN_ADMIN_ORIGINS=(ADMIN_ORIGIN,),
    WEBAUTHN_CHALLENGE_TTL_SECONDS=300,
    CACHES=LOCMEM_CACHE,
)
class WebAuthnBoundaryMiddlewareTests(SimpleTestCase):
    factory = RequestFactory()

    def setUp(self) -> None:
        for backend in caches.all():
            backend.clear()

    def _session(self, **values: object) -> CookieSessionStore:
        session = CookieSessionStore()
        for key, value in values.items():
            session[key] = value
        session.save()
        return session

    def _request(
        self,
        route: str,
        *,
        method: str,
        session: CookieSessionStore,
        credential: object | None = None,
        malformed_body: bytes | None = None,
        host: str = "api.joutak.ru",
    ):
        policy = WEBAUTHN_COMPLETION_POLICIES.get(route)
        if malformed_body is not None:
            body = malformed_body
        elif credential is None:
            body = b""
        else:
            payload = (
                {"credential": credential}
                if policy and policy.nested_credential
                else credential
            )
            body = json.dumps(payload).encode("utf-8")
        request = self.factory.generic(
            method,
            "/transport/path",
            data=body,
            content_type="application/json",
            HTTP_HOST=host,
        )
        request.session = session
        request.resolver_match = SimpleNamespace(view_name=route)
        return request

    def _options_response(
        self,
        route: str,
        *,
        challenge: str = CHALLENGE,
        status: int = 200,
    ) -> JsonResponse:
        policy = WEBAUTHN_OPTIONS_POLICIES[route]
        options = {"publicKey": {"challenge": challenge}}
        if policy.surface == "admin":
            payload = options
        else:
            option_key = (
                "creation_options"
                if policy.expected_type == WEBAUTHN_CREATE
                else "request_options"
            )
            payload = {"status": status, "data": {option_key: options}}
        response = JsonResponse(payload, status=status)
        if route.startswith("headless:app:"):
            response["X-Session-Token"] = "test-session-token"
        return response

    def _issue(
        self,
        route: str,
        session: CookieSessionStore,
        *,
        challenge: str = CHALLENGE,
        status: int = 200,
    ) -> JsonResponse:
        policy = WEBAUTHN_OPTIONS_POLICIES[route]
        if policy.purpose == "account.login" and status == 200:
            session[allauth_webauthn.STATE_SESSION_KEY] = {
                "challenge": challenge,
                "user_verification": "preferred",
            }
        request = self._request(route, method="GET", session=session)
        middleware = WebAuthnOriginValidationMiddleware(
            lambda _request: self._options_response(
                route,
                challenge=challenge,
                status=status,
            )
        )
        early_response = middleware.process_view(request, None, (), {})
        if early_response is not None:
            return early_response
        if route.startswith("headless:app:"):
            with patch(
                "accounts.middleware._boundary_session",
                return_value=SimpleNamespace(store=session, external=True),
            ):
                return middleware(request)
        return middleware(request)

    def test_passwordless_options_require_uv_for_app_and_browser(self):
        for client in ("app", "browser"):
            route = f"headless:{client}:mfa:login_webauthn"
            with self.subTest(client=client):
                session = self._session()
                response = self._issue(route, session)

                public_key = json.loads(response.content)["data"][
                    "request_options"
                ]["publicKey"]
                self.assertEqual(public_key["userVerification"], "required")
                state = session[allauth_webauthn.STATE_SESSION_KEY]
                self.assertEqual(state["user_verification"], "required")

    def test_passwordless_options_fail_closed_without_server_uv_state(self):
        route = "headless:browser:mfa:login_webauthn"
        session = self._session()
        request = self._request(route, method="GET", session=session)
        middleware = WebAuthnOriginValidationMiddleware(
            lambda _request: self._options_response(route)
        )

        response = middleware(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content),
            {"error": "Invalid WebAuthn response."},
        )
        self.assertNotIn(WEBAUTHN_CHALLENGE_SESSION_KEY, session)

    def _complete(
        self,
        route: str,
        session: CookieSessionStore,
        credential: object,
        *,
        malformed_body: bytes | None = None,
        host: str = "api.joutak.ru",
    ):
        policy = WEBAUTHN_COMPLETION_POLICIES[route]
        request = self._request(
            route,
            method=policy.method,
            session=session,
            credential=credential,
            malformed_body=malformed_body,
            host=host,
        )
        original_body = request.body
        middleware = WebAuthnOriginValidationMiddleware(
            lambda _request: JsonResponse({"ok": True})
        )
        response = middleware.process_view(request, None, (), {})
        return request, original_body, response

    def test_policy_covers_every_headless_completion_and_options_route(
        self,
    ) -> None:
        expected = {
            "login_webauthn": ("POST", "account.login"),
            "authenticate_webauthn": ("POST", "account.authenticate"),
            "reauthenticate_webauthn": ("POST", "account.reauthenticate"),
            "manage_webauthn": ("POST", "account.register"),
            "signup_webauthn": ("PUT", "account.signup"),
        }
        for client in ("app", "browser"):
            for suffix, (method, purpose) in expected.items():
                route = f"headless:{client}:mfa:{suffix}"
                with self.subTest(route=route):
                    self.assertEqual(
                        WEBAUTHN_COMPLETION_POLICIES[route].method,
                        method,
                    )
                    self.assertEqual(
                        WEBAUTHN_COMPLETION_POLICIES[route].purpose,
                        purpose,
                    )
                    self.assertIn(route, WEBAUTHN_OPTIONS_POLICIES)
                    self.assertEqual(
                        WEBAUTHN_OPTIONS_POLICIES[route].method,
                        "GET",
                    )

        self.assertEqual(
            WEBAUTHN_OPTIONS_POLICIES[
                "admin:admin_mfa_webauthn_options"
            ].method,
            "GET",
        )

    def test_current_headless_routes_resolve_to_guarded_names(self) -> None:
        routes = (
            "/api/auth/flow/app/v1/auth/webauthn/login",
            "/api/auth/flow/app/v1/auth/webauthn/authenticate",
            "/api/auth/flow/app/v1/auth/webauthn/reauthenticate",
            "/api/auth/flow/app/v1/account/authenticators/webauthn",
        )
        for path in routes:
            with self.subTest(path=path):
                self.assertIn(
                    resolve(path).view_name,
                    WEBAUTHN_COMPLETION_POLICIES,
                )

    def test_metadata_is_written_only_after_successful_options_response(
        self,
    ) -> None:
        route = "headless:browser:mfa:login_webauthn"
        session = self._session()

        response = self._issue(route, session)

        self.assertEqual(response.status_code, 200)
        metadata = session[WEBAUTHN_CHALLENGE_SESSION_KEY]
        self.assertEqual(metadata["purpose"], "account.login")
        self.assertNotIn("origin", metadata)
        self.assertNotIn(CHALLENGE, metadata.values())
        self.assertIn(WEBAUTHN_SESSION_BINDING_KEY, session)

        failed = self._issue(route, session, status=400)
        self.assertEqual(failed.status_code, 400)
        self.assertNotIn(WEBAUTHN_CHALLENGE_SESSION_KEY, session)

    def test_exact_account_origin_and_matching_challenge_pass_unchanged(
        self,
    ) -> None:
        route = "headless:browser:mfa:login_webauthn"
        session = self._session()
        self._issue(route, session)

        request, original_body, response = self._complete(
            route,
            session,
            _credential(),
        )

        self.assertIsNone(response)
        self.assertEqual(request.body, original_body)
        self.assertNotIn(WEBAUTHN_CHALLENGE_SESSION_KEY, session)

        self._issue(route, session)
        _, _, rejected = self._complete(
            route,
            session,
            _credential(origin=API_ORIGIN),
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(
            json.loads(rejected.content),
            {"error": "Invalid WebAuthn response."},
        )

    def test_registration_requires_create_type_and_authenticated_subject(
        self,
    ) -> None:
        route = "headless:browser:mfa:manage_webauthn"
        session = self._session(**{SESSION_KEY: "101"})
        self._issue(route, session)
        _, _, valid = self._complete(
            route,
            session,
            _credential(ceremony_type=WEBAUTHN_CREATE),
        )
        self.assertIsNone(valid)

        self._issue(route, session)
        _, _, invalid = self._complete(route, session, _credential())
        self.assertEqual(invalid.status_code, 400)

    def test_admin_route_uses_admin_origin_and_pending_flow_binding(
        self,
    ) -> None:
        route = "admin:admin_mfa_webauthn_complete"
        options_route = "admin:admin_mfa_webauthn_options"
        pending = {
            "version": 1,
            "user_pk": "101",
            "started_at": time.time(),
            "next": "/admin/",
            "flow_id": "f" * 32,
        }
        session = self._session(**{SESSION_KEY_ADMIN_MFA_PENDING: pending})
        self._issue(options_route, session)
        _, _, valid = self._complete(
            route,
            session,
            _credential(origin=ADMIN_ORIGIN),
        )
        self.assertIsNone(valid)

        self._issue(options_route, session)
        with patch(
            "accounts.middleware._register_admin_boundary_failure",
            return_value=None,
        ):
            _, _, invalid = self._complete(route, session, _credential())
        self.assertEqual(invalid.status_code, 400)

    def test_expired_challenge_is_consumed_and_rejected(self) -> None:
        route = "headless:browser:mfa:login_webauthn"
        session = self._session()
        with patch("accounts.middleware.time.time", return_value=100.0):
            self._issue(route, session)

        with patch("accounts.middleware.time.time", return_value=401.0):
            _, _, response = self._complete(route, session, _credential())

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(WEBAUTHN_CHALLENGE_SESSION_KEY, session)

    def test_cross_purpose_completion_is_rejected(self) -> None:
        session = self._session(**{SESSION_KEY: "101"})
        self._issue("headless:browser:mfa:login_webauthn", session)

        _, _, response = self._complete(
            "headless:browser:mfa:reauthenticate_webauthn",
            session,
            _credential(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(WEBAUTHN_CHALLENGE_SESSION_KEY, session)

    def test_different_session_cannot_complete_challenge(self) -> None:
        issuer_session = self._session()
        other_session = self._session()
        route = "headless:browser:mfa:login_webauthn"
        self._issue(route, issuer_session)

        _, _, response = self._complete(route, other_session, _credential())

        self.assertEqual(response.status_code, 400)
        self.assertIn(WEBAUTHN_CHALLENGE_SESSION_KEY, issuer_session)

    def test_authenticated_subject_change_invalidates_registration(
        self,
    ) -> None:
        route = "headless:browser:mfa:manage_webauthn"
        session = self._session(**{SESSION_KEY: "101"})
        self._issue(route, session)
        session[SESSION_KEY] = "202"

        _, _, response = self._complete(
            route,
            session,
            _credential(ceremony_type=WEBAUTHN_CREATE),
        )

        self.assertEqual(response.status_code, 400)

    def test_signed_challenge_must_match_options(self) -> None:
        route = "headless:browser:mfa:login_webauthn"
        session = self._session()
        self._issue(route, session)

        _, _, response = self._complete(
            route,
            session,
            _credential(challenge=OTHER_CHALLENGE),
        )

        self.assertEqual(response.status_code, 400)

    def test_shared_nonce_claim_rejects_stale_session_replay(self) -> None:
        route = "headless:browser:mfa:login_webauthn"
        first_session = self._session()
        self._issue(route, first_session)
        cloned_session = self._session()
        for key, value in copy.deepcopy(dict(first_session.items())).items():
            cloned_session[key] = value
        cloned_session.save()

        _, _, first_response = self._complete(
            route,
            first_session,
            _credential(),
        )
        _, _, replay_response = self._complete(
            route,
            cloned_session,
            _credential(),
        )

        self.assertIsNone(first_response)
        self.assertEqual(replay_response.status_code, 400)

    def test_malformed_completion_consumes_challenge(self) -> None:
        route = "headless:browser:mfa:login_webauthn"
        session = self._session()
        self._issue(route, session)

        _, _, response = self._complete(
            route,
            session,
            {},
            malformed_body=b"not-json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(WEBAUTHN_CHALLENGE_SESSION_KEY, session)

    def test_non_completion_method_is_not_intercepted(self) -> None:
        route = "headless:browser:mfa:manage_webauthn"
        session = self._session()
        request = self._request(route, method="PUT", session=session)
        middleware = WebAuthnOriginValidationMiddleware(
            lambda _request: JsonResponse({"ok": True})
        )
        self.assertIsNone(middleware.process_view(request, None, (), {}))

    def test_rejection_log_contains_reason_but_no_signed_data(self) -> None:
        route = "headless:browser:mfa:login_webauthn"
        hostile_origin = "https://do-not-log.example"
        session = self._session()
        self._issue(route, session)

        with self.assertLogs("accounts.middleware", level="WARNING") as logs:
            _, _, response = self._complete(
                route,
                session,
                _credential(origin=hostile_origin),
            )

        self.assertEqual(response.status_code, 400)
        combined = "\n".join(logs.output)
        self.assertIn("reason=origin_not_allowed", combined)
        self.assertNotIn(hostile_origin, combined)
        self.assertNotIn(CHALLENGE, combined)
        self.assertNotIn("clientDataJSON", combined)
        record = logs.records[-1]
        self.assertEqual(record.request_host, "api.joutak.ru")
        self.assertEqual(record.request_method, "POST")
        self.assertEqual(record.route, route)

    def test_rejection_logging_cannot_mask_invalid_host_response(self) -> None:
        route = "headless:browser:mfa:login_webauthn"
        session = self._session()
        self._issue(route, session)

        with self.assertLogs("accounts.middleware", level="WARNING") as logs:
            _, _, response = self._complete(
                route,
                session,
                _credential(origin="https://do-not-log.example"),
                host="not-allowed.example",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(logs.records[-1].request_host, "<invalid>")

    def test_options_and_completion_responses_are_no_store(self) -> None:
        session = self._session()
        routes_and_methods = (
            ("headless:browser:mfa:login_webauthn", "GET"),
            ("headless:browser:mfa:login_webauthn", "POST"),
            ("admin:admin_mfa_webauthn_options", "POST"),
        )
        for route, method in routes_and_methods:
            with self.subTest(route=route, method=method):
                request = self._request(route, method=method, session=session)
                middleware = WebAuthnOriginValidationMiddleware(
                    lambda _request: JsonResponse({"ok": True})
                )
                response = middleware(request)
                directives = response.headers["Cache-Control"]
                self.assertIn("no-store", directives)
                self.assertIn("private", directives)


@override_settings(
    ACCOUNT_RATE_LIMITS=False,
    CACHES=LOCMEM_CACHE,
    ALLOWED_HOSTS=(
        "testserver",
        "joutak.ru",
        "api.joutak.ru",
        "admin.joutak.ru",
    ),
    DJANGO_API_HOSTS=("api.joutak.ru",),
    DJANGO_ADMIN_HOSTS=("admin.joutak.ru",),
    WEBAUTHN_RP_ID="joutak.ru",
    WEBAUTHN_RP_NAME="JouTak",
    WEBAUTHN_ACCOUNT_ORIGINS=(ACCOUNT_ORIGIN,),
    WEBAUTHN_ADMIN_ORIGINS=(ADMIN_ORIGIN,),
    WEBAUTHN_CHALLENGE_TTL_SECONDS=300,
)
class WebAuthnOptionsIntegrationTests(APITestCase):
    def setUp(self) -> None:
        super().setUp()
        for backend in caches.all():
            backend.clear()

    def _reauthenticate(self, token: str, *, host: str) -> None:
        response = self.headless_post_json(
            "/auth/reauthenticate",
            {"password": self.default_password},
            **self.auth_headers(token),
            HTTP_HOST=host,
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_app_passwordless_options_and_server_state_require_uv(
        self,
    ) -> None:
        app_path = self.headless("/auth/webauthn/login")
        app_response = self.client.get(
            app_path,
            HTTP_HOST="api.joutak.ru",
        )
        self.assertEqual(app_response.status_code, 200, app_response.content)
        self.assertEqual(
            app_response.json()["data"]["request_options"]["publicKey"][
                "userVerification"
            ],
            "required",
        )
        token = self.session_token(app_response)
        self.assertTrue(token)
        app_session = headless_app_settings.TOKEN_STRATEGY.lookup_session(
            token
        )
        self.assertEqual(
            app_session[allauth_webauthn.STATE_SESSION_KEY][
                "user_verification"
            ],
            "required",
        )

    def test_registration_options_use_canonical_rp_on_primary_and_api_hosts(
        self,
    ) -> None:
        auth = self.signup_and_auth()
        token = auth["session_token"]
        user = get_user_model().objects.get(email=auth["email"].lower())
        EmailAddress.objects.update_or_create(
            user=user,
            email=auth["email"].lower(),
            defaults={"primary": True, "verified": True},
        )
        self._reauthenticate(token, host="joutak.ru")

        for host in ("joutak.ru", "api.joutak.ru"):
            with self.subTest(host=host):
                response = self.client.get(
                    self.headless("/account/authenticators/webauthn"),
                    **self.auth_headers(token),
                    HTTP_HOST=host,
                )
                self.assertEqual(response.status_code, 200, response.content)
                rp = response.json()["data"]["creation_options"]["publicKey"][
                    "rp"
                ]
                self.assertEqual(rp["id"], "joutak.ru")
                self.assertEqual(rp["name"], "JouTak")
                self.assertIn("no-store", response.headers["Cache-Control"])

        blocked = self.client.get(
            self.headless("/account/authenticators/webauthn"),
            **self.auth_headers(token),
            HTTP_HOST="admin.joutak.ru",
        )
        self.assertEqual(blocked.status_code, 403)

    def test_api_transport_still_requires_signed_account_origin(self) -> None:
        path = self.headless("/auth/webauthn/login")
        options = self.client.get(path, HTTP_HOST="api.joutak.ru")
        self.assertEqual(options.status_code, 200, options.content)
        token = self.session_token(options)
        self.assertTrue(token)
        challenge = options.json()["data"]["request_options"]["publicKey"][
            "challenge"
        ]

        request = RequestFactory().post(
            path,
            data=json.dumps(
                {
                    "credential": _credential(
                        origin=ACCOUNT_ORIGIN,
                        challenge=challenge,
                    )
                }
            ),
            content_type="application/json",
            HTTP_HOST="api.joutak.ru",
            HTTP_X_SESSION_TOKEN=token,
        )
        request.resolver_match = resolve(path)
        middleware = WebAuthnOriginValidationMiddleware(
            lambda _request: JsonResponse({"ok": True})
        )
        original_body = request.body
        self.assertIsNone(middleware.process_view(request, None, (), {}))
        self.assertEqual(request.body, original_body)

        options = self.client.get(
            path,
            HTTP_HOST="api.joutak.ru",
            HTTP_X_SESSION_TOKEN=token,
        )
        challenge = options.json()["data"]["request_options"]["publicKey"][
            "challenge"
        ]
        rejected = RequestFactory().post(
            path,
            data=json.dumps(
                {
                    "credential": _credential(
                        origin=API_ORIGIN,
                        challenge=challenge,
                    )
                }
            ),
            content_type="application/json",
            HTTP_HOST="api.joutak.ru",
            HTTP_X_SESSION_TOKEN=token,
        )
        rejected.resolver_match = resolve(path)
        response = middleware.process_view(rejected, None, (), {})
        self.assertEqual(response.status_code, 400)

    def test_admin_authentication_options_use_canonical_rp_id(self) -> None:
        user = get_user_model().objects.create_user(
            username="admin_rp",
            email="admin-rp@example.com",
            password=self.default_password,
            is_staff=True,
        )
        Authenticator.objects.create(
            user=user,
            type=Authenticator.Type.WEBAUTHN,
            data={},
        )
        session = self.client.session
        session[SESSION_KEY_ADMIN_MFA_PENDING] = {
            "version": 1,
            "user_pk": str(user.pk),
            "started_at": time.time(),
            "next": "/admin/",
            "flow_id": "a" * 32,
        }
        session.save()

        with patch.object(
            allauth_webauthn, "get_credentials", return_value=[]
        ):
            response = self.client.get(
                "/admin/mfa-verify/webauthn-options/",
                HTTP_HOST="admin.joutak.ru",
            )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["publicKey"]["rpId"], "joutak.ru")
        self.assertIn("no-store", response.headers["Cache-Control"])


@override_settings(
    CACHES=LOCMEM_CACHE,
    ALLOWED_HOSTS=("admin.joutak.ru",),
    DJANGO_ADMIN_HOSTS=("admin.joutak.ru",),
    DJANGO_API_HOSTS=(),
    WEBAUTHN_ADMIN_ORIGINS=(ADMIN_ORIGIN,),
    WEBAUTHN_CHALLENGE_TTL_SECONDS=300,
    ADMIN_MFA_COMPLETION_RATE="1/m",
)
class AdminWebAuthnBoundaryQuotaTests(TestCase):
    def setUp(self) -> None:
        for backend in caches.all():
            backend.clear()
        self.user = get_user_model().objects.create_user(
            username="boundary_admin",
            email="boundary-admin@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        Authenticator.objects.create(
            user=self.user,
            type=Authenticator.Type.WEBAUTHN,
            data={},
        )
        session = self.client.session
        session[SESSION_KEY_ADMIN_MFA_PENDING] = {
            "version": 1,
            "user_pk": str(self.user.pk),
            "started_at": time.time(),
            "next": "/admin/",
            "flow_id": "q" * 32,
        }
        session.save()

    def _options(self) -> str:
        def fake_begin(*, user):
            allauth_context.request.session[
                allauth_webauthn.STATE_SESSION_KEY
            ] = {
                "challenge": CHALLENGE,
                "user_verification": "preferred",
            }
            return {
                "publicKey": {
                    "challenge": CHALLENGE,
                    "userVerification": "preferred",
                }
            }

        with patch.object(
            allauth_webauthn,
            "begin_authentication",
            side_effect=fake_begin,
        ):
            response = self.client.get(
                "/admin/mfa-verify/webauthn-options/",
                HTTP_HOST="admin.joutak.ru",
            )
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["publicKey"]["challenge"]

    def test_malformed_and_hostile_attempts_share_quota_and_429_clears_flow(
        self,
    ) -> None:
        self._options()
        malformed = self.client.post(
            "/admin/mfa-verify/webauthn-complete/",
            data=b"not-json",
            content_type="application/json",
            HTTP_HOST="admin.joutak.ru",
            HTTP_ORIGIN=ADMIN_ORIGIN,
            secure=True,
        )
        self.assertEqual(malformed.status_code, 400)
        self.assertIn(SESSION_KEY_ADMIN_MFA_PENDING, self.client.session)

        challenge = self._options()
        with self.assertLogs("accounts.middleware", level="WARNING") as logs:
            limited = self.client.post(
                "/admin/mfa-verify/webauthn-complete/",
                data=json.dumps(
                    _credential(
                        origin=ACCOUNT_ORIGIN,
                        challenge=challenge,
                    )
                ),
                content_type="application/json",
                HTTP_HOST="admin.joutak.ru",
                HTTP_ORIGIN=ADMIN_ORIGIN,
                secure=True,
            )

        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited.headers["Retry-After"], "60")
        self.assertEqual(
            limited.json(),
            {"error": "Invalid WebAuthn response."},
        )
        self.assertNotIn(SESSION_KEY_ADMIN_MFA_PENDING, self.client.session)
        self.assertNotIn(WEBAUTHN_CHALLENGE_SESSION_KEY, self.client.session)
        combined = "\n".join(logs.output)
        self.assertIn(
            "admin.mfa.rate_limited",
            {getattr(record, "event", None) for record in logs.records},
        )
        self.assertNotIn(ACCOUNT_ORIGIN, combined)
        self.assertNotIn(CHALLENGE, combined)


class CanonicalWebAuthnRPAdapterTests(SimpleTestCase):
    factory = RequestFactory()

    @override_settings(
        WEBAUTHN_RP_ID="joutak.ru",
        WEBAUTHN_RP_NAME="JouTak",
    )
    def test_rp_entity_is_independent_of_request_host(self) -> None:
        adapter = EncryptedMFAAdapter()
        hosts = (
            "joutak.ru",
            "api.joutak.ru",
            "admin.joutak.ru",
            "localhost:8000",
        )
        for host in hosts:
            with self.subTest(host=host):
                request = self.factory.get("/", HTTP_HOST=host)
                with allauth_context.request_context(request):
                    self.assertEqual(
                        adapter.get_public_key_credential_rp_entity(),
                        {"id": "joutak.ru", "name": "JouTak"},
                    )
