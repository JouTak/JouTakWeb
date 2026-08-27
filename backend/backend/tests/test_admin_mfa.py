from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from accounts.services.admin_mfa import (
    SESSION_KEY_ADMIN_MFA_ASSURANCE,
    SESSION_KEY_ADMIN_MFA_PENDING,
    AdminMFARateLimitError,
    AdminMFAVerificationError,
    abort_pending_admin_login,
    admin_request_has_mfa_assurance,
    admin_user_has_primary_mfa,
    begin_admin_webauthn,
    complete_admin_login,
    get_pending_admin_login,
    safe_admin_next,
    start_pending_admin_login,
    verify_admin_code,
    verify_admin_webauthn,
)
from accounts.webauthn import WEBAUTHN_CHALLENGE_SESSION_KEY
from allauth.core import context as allauth_context
from allauth.mfa.models import Authenticator
from allauth.mfa.recovery_codes.internal.auth import RecoveryCodes
from allauth.mfa.totp.internal.auth import (
    TOTP,
    format_hotp_value,
    hotp_value,
    yield_hotp_counters_from_time,
)
from allauth.mfa.webauthn.internal import auth as allauth_webauthn
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import caches
from django.core.management import call_command
from django.test import (
    Client,
    RequestFactory,
    TestCase,
    TransactionTestCase,
    override_settings,
)

User = get_user_model()
TOTP_SECRET = "JBSWY3DPEHPK3PXP"


@override_settings(
    DJANGO_ALLOWED_HOSTS=(
        "localhost",
        "admin.localhost",
        "api.localhost",
    ),
    DJANGO_ADMIN_HOSTS=("admin.localhost",),
    DJANGO_API_HOSTS=("api.localhost",),
    FRONTEND_BASE_URL="http://localhost:8080",
    WEBAUTHN_ADMIN_ORIGINS=("http://admin.localhost",),
    ADMIN_MFA_PENDING_TTL_SECONDS=300,
    ADMIN_MFA_ASSURANCE_TTL_SECONDS=28800,
)
class AdminMFAFlowTests(TestCase):
    def setUp(self) -> None:
        for backend in caches.all():
            backend.clear()
        self.factory = RequestFactory()

    def _staff(self, username: str = "staff"):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="StrongPass123!",
            is_staff=True,
        )

    def _activate_totp(self, user) -> Authenticator:
        return TOTP.activate(user, TOTP_SECRET).instance

    def _totp_code(self) -> str:
        counter = next(yield_hotp_counters_from_time())
        return format_hotp_value(hotp_value(TOTP_SECRET, counter))

    def _request(self, *, method: str = "post"):
        request_factory = getattr(self.factory, method)
        request = request_factory(
            "/admin/mfa-verify/",
            HTTP_HOST="admin.localhost",
            REMOTE_ADDR="203.0.113.10",
        )
        SessionMiddleware(lambda _request: None).process_request(request)
        request.session.save()
        request.user = AnonymousUser()
        return request

    def _pending_for(self, request, user, *, next_url="/admin/"):
        return start_pending_admin_login(
            request,
            user,
            next_url=next_url,
        )

    def _mark_assured(
        self,
        user,
        *,
        verified_at: float | None = None,
        method: str = "totp",
    ) -> None:
        session = self.client.session
        session[SESSION_KEY_ADMIN_MFA_ASSURANCE] = {
            "version": 1,
            "user_pk": str(user.pk),
            "verified_at": verified_at or time.time(),
            "method": method,
        }
        session.save()

    def test_recovery_codes_alone_are_not_primary_admin_mfa(self):
        user = self._staff("recovery_only")
        RecoveryCodes.activate(user)

        self.assertFalse(admin_user_has_primary_mfa(user))
        self.client.force_login(user)
        self._mark_assured(user, method="recovery_code")

        response = self.client.get(
            "/admin/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_expired_pending_flow_is_cleared(self):
        user = self._staff("expired_pending")
        self._activate_totp(user)
        self.client.force_login(user)
        self._mark_assured(user)
        session = self.client.session
        session[SESSION_KEY_ADMIN_MFA_PENDING] = {
            "version": 1,
            "user_pk": str(user.pk),
            "started_at": time.time() - 301,
            "next": "/admin/",
            "flow_id": "p" * 32,
        }
        session.save()

        response = self.client.get(
            "/admin/mfa-verify/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/login/")
        self.assertNotIn(SESSION_KEY_ADMIN_MFA_PENDING, self.client.session)
        self.assertIn(SESSION_KEY_ADMIN_MFA_ASSURANCE, self.client.session)

    def test_missing_pending_flow_does_not_clear_existing_assurance(self):
        user = self._staff("assured_without_pending")
        self._activate_totp(user)
        self.client.force_login(user)
        self._mark_assured(user)

        verify_response = self.client.get(
            "/admin/mfa-verify/",
            HTTP_HOST="admin.localhost",
        )
        options_response = self.client.get(
            "/admin/mfa-verify/webauthn-options/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(verify_response.status_code, 302)
        self.assertEqual(options_response.status_code, 403)
        session = self.client.session
        self.assertIn(SESSION_KEY_ADMIN_MFA_ASSURANCE, session)
        self.assertEqual(session["_auth_user_id"], str(user.pk))

    def test_admin_mfa_endpoints_reject_wrong_methods_without_side_effects(
        self,
    ):
        user = self._staff("wrong_methods")
        self._activate_totp(user)
        self.client.post(
            "/admin/login/",
            {
                "username": user.username,
                "password": "StrongPass123!",
            },
            HTTP_HOST="admin.localhost",
            HTTP_ORIGIN="http://admin.localhost",
        )
        pending = self.client.session[SESSION_KEY_ADMIN_MFA_PENDING]

        with (
            patch("backend.admin_site.begin_admin_webauthn") as begin_mock,
            patch("backend.admin_site.verify_admin_webauthn") as webauthn_mock,
            patch("backend.admin_site.verify_admin_code") as code_mock,
        ):
            options_response = self.client.post(
                "/admin/mfa-verify/webauthn-options/",
                HTTP_HOST="admin.localhost",
                HTTP_ORIGIN="http://admin.localhost",
            )
            completion_response = self.client.generic(
                "GET",
                "/admin/mfa-verify/webauthn-complete/",
                data=b'{"credential":"must-not-be-read"}',
                content_type="application/json",
                HTTP_HOST="admin.localhost",
            )
            verify_response = self.client.put(
                "/admin/mfa-verify/",
                data={"mfa_code": "must-not-be-read"},
                HTTP_HOST="admin.localhost",
                HTTP_ORIGIN="http://admin.localhost",
            )

        self.assertEqual(options_response.status_code, 405)
        self.assertEqual(options_response.headers["Allow"], "GET")
        self.assertEqual(completion_response.status_code, 405)
        self.assertEqual(completion_response.headers["Allow"], "POST")
        self.assertEqual(verify_response.status_code, 405)
        self.assertEqual(verify_response.headers["Allow"], "GET, POST")
        begin_mock.assert_not_called()
        webauthn_mock.assert_not_called()
        code_mock.assert_not_called()

        session = self.client.session
        self.assertEqual(session[SESSION_KEY_ADMIN_MFA_PENDING], pending)
        self.assertNotIn(allauth_webauthn.STATE_SESSION_KEY, session)
        self.assertNotIn(WEBAUTHN_CHALLENGE_SESSION_KEY, session)
        self.assertNotIn(SESSION_KEY_ADMIN_MFA_ASSURANCE, session)
        self.assertNotIn("_auth_user_id", session)

    def test_expired_or_other_user_assurance_is_fail_closed(self):
        first = self._staff("assured_first")
        second = self._staff("assured_second")
        self._activate_totp(first)
        self._activate_totp(second)
        self.client.force_login(second)
        self._mark_assured(first)

        response = self.client.get(
            "/admin/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

        self.client.force_login(second)
        self._mark_assured(second, verified_at=time.time() - 28801)
        response = self.client.get(
            "/admin/",
            HTTP_HOST="admin.localhost",
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_removing_last_primary_factor_revokes_next_request(self):
        user = self._staff("removed_factor")
        authenticator = self._activate_totp(user)
        self.client.force_login(user)
        self._mark_assured(user)
        authenticator.delete()

        response = self.client.get(
            "/admin/",
            HTTP_HOST="admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_role_or_active_status_removal_clears_assurance(self):
        for field in ("is_staff", "is_active"):
            with self.subTest(field=field):
                user = self._staff(f"removed_{field}")
                self._activate_totp(user)
                request = self._request()
                request.user = user
                request.session[SESSION_KEY_ADMIN_MFA_ASSURANCE] = {
                    "version": 1,
                    "user_pk": str(user.pk),
                    "verified_at": time.time(),
                    "method": "totp",
                }
                setattr(user, field, False)

                self.assertFalse(admin_request_has_mfa_assurance(request))
                self.assertNotIn(
                    SESSION_KEY_ADMIN_MFA_ASSURANCE,
                    request.session,
                )

    def test_totp_login_rotates_session_and_records_assurance(self):
        user = self._staff("rotated")
        authenticator = self._activate_totp(user)
        session = self.client.session
        session["pre_login_marker"] = True
        session.save()
        original_key = session.session_key

        password_response = self.client.post(
            "/admin/login/",
            {
                "username": user.username,
                "password": "StrongPass123!",
                "next": "https://evil.example/steal",
            },
            HTTP_HOST="admin.localhost",
            HTTP_ORIGIN="http://admin.localhost",
        )

        self.assertEqual(password_response.status_code, 302)
        pending_key = self.client.session.session_key
        self.assertNotEqual(pending_key, original_key)
        self.assertEqual(
            self.client.session[SESSION_KEY_ADMIN_MFA_PENDING]["next"],
            "/admin/",
        )

        verify_response = self.client.post(
            "/admin/mfa-verify/",
            {"mfa_code": self._totp_code()},
            HTTP_HOST="admin.localhost",
            HTTP_ORIGIN="http://admin.localhost",
        )

        self.assertEqual(verify_response.status_code, 302)
        self.assertEqual(verify_response["Location"], "/admin/")
        final_session = self.client.session
        self.assertNotEqual(final_session.session_key, pending_key)
        self.assertNotIn(SESSION_KEY_ADMIN_MFA_PENDING, final_session)
        assurance = final_session[SESSION_KEY_ADMIN_MFA_ASSURANCE]
        self.assertEqual(assurance["user_pk"], str(user.pk))
        self.assertEqual(assurance["method"], "totp")
        self.assertLessEqual(assurance["verified_at"], time.time())
        records = final_session["account_authentication_methods"]
        self.assertTrue(
            any(
                record.get("method") == "mfa"
                and record.get("type") == Authenticator.Type.TOTP
                and record.get("id") == authenticator.pk
                for record in records
            )
        )
        authenticator.refresh_from_db()
        self.assertIsNotNone(authenticator.last_used_at)

    def test_primary_mfa_removal_after_password_validation_is_not_a_500(self):
        user = self._staff("mfa_removed_during_login")
        authenticator = self._activate_totp(user)

        def remove_factor_then_start(request, pending_user, *, next_url):
            authenticator.delete()
            return start_pending_admin_login(
                request,
                pending_user,
                next_url=next_url,
            )

        with patch(
            "backend.admin_site.start_pending_admin_login",
            side_effect=remove_factor_then_start,
        ):
            response = self.client.post(
                "/admin/login/",
                {
                    "username": user.username,
                    "password": "StrongPass123!",
                },
                HTTP_HOST="admin.localhost",
                HTTP_ORIGIN="http://admin.localhost",
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Не удалось начать подтверждение.")
        session = self.client.session
        self.assertNotIn(SESSION_KEY_ADMIN_MFA_PENDING, session)
        self.assertNotIn(SESSION_KEY_ADMIN_MFA_ASSURANCE, session)
        self.assertNotIn("_auth_user_id", session)

    def test_safe_admin_next_is_restored_after_mfa(self):
        user = self._staff("safe_next")
        self._activate_totp(user)
        expected = "/admin/auth/user/?q=staff"

        response = self.client.post(
            "/admin/login/",
            {
                "username": user.username,
                "password": "StrongPass123!",
                "next": expected,
            },
            HTTP_HOST="admin.localhost",
            HTTP_ORIGIN="http://admin.localhost",
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.post(
            "/admin/mfa-verify/",
            {"mfa_code": self._totp_code()},
            HTTP_HOST="admin.localhost",
            HTTP_ORIGIN="http://admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], expected)

    def test_safe_admin_next_rejects_path_normalization_escapes(self):
        request = self.factory.get(
            "/admin/login/",
            HTTP_HOST="admin.localhost",
        )

        for candidate in (
            "/admin/../outside",
            "/admin/%2e%2e/outside",
            "/admin/%252e%252e/outside",
            "/admin/..\\outside",
        ):
            with self.subTest(candidate=candidate):
                self.assertEqual(
                    safe_admin_next(request, candidate),
                    "/admin/",
                )

    def test_recovery_code_is_recorded_and_consumed_once(self):
        user = self._staff("recovery")
        self._activate_totp(user)
        recovery = RecoveryCodes.activate(user)
        recovery_code = recovery.get_unused_codes()[0]

        self.client.post(
            "/admin/login/",
            {
                "username": user.username,
                "password": "StrongPass123!",
            },
            HTTP_HOST="admin.localhost",
            HTTP_ORIGIN="http://admin.localhost",
        )
        response = self.client.post(
            "/admin/mfa-verify/",
            {"mfa_code": recovery_code},
            HTTP_HOST="admin.localhost",
            HTTP_ORIGIN="http://admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.client.session[SESSION_KEY_ADMIN_MFA_ASSURANCE]["method"],
            "recovery_code",
        )
        recovery.instance.refresh_from_db()
        self.assertIsNotNone(recovery.instance.last_used_at)
        self.assertNotIn(
            recovery_code,
            recovery.instance.wrap().get_unused_codes(),
        )

        self.client.post(
            "/admin/logout/",
            HTTP_HOST="admin.localhost",
            HTTP_ORIGIN="http://admin.localhost",
        )
        self.client.post(
            "/admin/login/",
            {
                "username": user.username,
                "password": "StrongPass123!",
            },
            HTTP_HOST="admin.localhost",
            HTTP_ORIGIN="http://admin.localhost",
        )
        response = self.client.post(
            "/admin/mfa-verify/",
            {"mfa_code": recovery_code},
            HTTP_HOST="admin.localhost",
            HTTP_ORIGIN="http://admin.localhost",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Неверный код")

    @override_settings(ADMIN_MFA_COMPLETION_RATE="1/m")
    def test_code_and_webauthn_limits_survive_fresh_password_flow(self):
        user = self._staff("separate_limits")
        self._activate_totp(user)
        request = self._request()
        pending = self._pending_for(request, user)

        with allauth_context.request_context(request):
            with self.assertRaises(AdminMFAVerificationError):
                verify_admin_code(request, pending, "wrong")
            with self.assertRaises(AdminMFAVerificationError):
                verify_admin_webauthn(request, pending, {})
            with self.assertRaises(AdminMFARateLimitError):
                verify_admin_code(request, pending, "wrong-again")
            with self.assertRaises(AdminMFARateLimitError):
                verify_admin_webauthn(request, pending, {})

        abort_pending_admin_login(request, pending)
        self.assertIsNone(get_pending_admin_login(request))
        fresh = self._pending_for(request, user)
        self.assertNotEqual(fresh.flow_id, pending.flow_id)
        with allauth_context.request_context(request):
            with self.assertRaises(AdminMFARateLimitError):
                verify_admin_code(request, fresh, "wrong-after-restart")
            with self.assertRaises(AdminMFARateLimitError):
                verify_admin_webauthn(request, fresh, {})

    @override_settings(
        ADMIN_MFA_COMPLETION_RATE="1/m",
        ADMIN_MFA_OPTIONS_RATE="1/m",
    )
    def test_success_rotates_all_rate_groups_for_next_login(self):
        user = self._staff("successful_rate_reset")
        self._activate_totp(user)
        Authenticator.objects.create(
            user=user,
            type=Authenticator.Type.WEBAUTHN,
            data={},
        )
        request = self._request()
        pending = self._pending_for(request, user)

        def fake_begin(*, user):
            allauth_context.request.session[
                allauth_webauthn.STATE_SESSION_KEY
            ] = {
                "challenge": "Y2hhbGxlbmdl",
                "user_verification": "preferred",
            }
            return {
                "publicKey": {
                    "challenge": "Y2hhbGxlbmdl",
                    "userVerification": "preferred",
                }
            }

        with patch.object(
            allauth_webauthn,
            "begin_authentication",
            side_effect=fake_begin,
        ):
            with allauth_context.request_context(request):
                begin_admin_webauthn(request, pending)
                with self.assertRaises(AdminMFAVerificationError):
                    verify_admin_code(request, pending, "wrong")
                with self.assertRaises(AdminMFAVerificationError):
                    verify_admin_webauthn(request, pending, {})
                verification = verify_admin_code(
                    request,
                    pending,
                    self._totp_code(),
                )
                complete_admin_login(request, pending, verification)

        next_request = self._request()
        next_pending = self._pending_for(next_request, user)
        with patch.object(
            allauth_webauthn,
            "begin_authentication",
            side_effect=fake_begin,
        ):
            with allauth_context.request_context(next_request):
                begin_admin_webauthn(next_request, next_pending)
                with self.assertRaises(AdminMFAVerificationError):
                    verify_admin_code(next_request, next_pending, "wrong")
                with self.assertRaises(AdminMFAVerificationError):
                    verify_admin_webauthn(next_request, next_pending, {})

    def test_rate_epoch_cache_failure_is_fail_closed(self):
        user = self._staff("rate_cache_failure")
        self._activate_totp(user)
        request = self._request()
        pending = self._pending_for(request, user)

        with patch.object(
            caches["ratelimit"],
            "add",
            side_effect=RuntimeError("cache unavailable"),
        ):
            with self.assertRaises(AdminMFARateLimitError) as raised:
                verify_admin_code(request, pending, self._totp_code())

        self.assertEqual(
            raised.exception.reason_code,
            "rate_limit_backend_unavailable",
        )

    @override_settings(ADMIN_MFA_OPTIONS_RATE="1/m")
    def test_admin_webauthn_options_require_uv_and_are_flow_limited(self):
        user = self._staff("required_uv")
        Authenticator.objects.create(
            user=user,
            type=Authenticator.Type.WEBAUTHN,
            data={},
        )
        request = self._request(method="get")
        pending = self._pending_for(request, user)

        def fake_begin(*, user):
            request.session[allauth_webauthn.STATE_SESSION_KEY] = {
                "challenge": "Y2hhbGxlbmdl",
                "user_verification": "preferred",
            }
            return {
                "publicKey": {
                    "challenge": "Y2hhbGxlbmdl",
                    "userVerification": "preferred",
                }
            }

        with patch.object(
            allauth_webauthn,
            "begin_authentication",
            side_effect=fake_begin,
        ):
            with allauth_context.request_context(request):
                options = begin_admin_webauthn(request, pending)

        self.assertEqual(
            options["publicKey"]["userVerification"],
            "required",
        )
        state = request.session[allauth_webauthn.STATE_SESSION_KEY]
        self.assertEqual(state["user_verification"], "required")
        with self.assertRaises(AdminMFARateLimitError):
            begin_admin_webauthn(request, pending)

    def test_sequential_requests_keep_allauth_context_isolated(self):
        first_user = self._staff("context_first")
        second_user = self._staff("context_second")
        for user in (first_user, second_user):
            Authenticator.objects.create(
                user=user,
                type=Authenticator.Type.WEBAUTHN,
                data={},
            )

        second_client = Client()
        clients_and_flows = (
            (self.client, first_user, "a" * 32),
            (second_client, second_user, "b" * 32),
        )
        for client, user, flow_id in clients_and_flows:
            session = client.session
            session[SESSION_KEY_ADMIN_MFA_PENDING] = {
                "version": 1,
                "user_pk": str(user.pk),
                "started_at": time.time(),
                "next": "/admin/",
                "flow_id": flow_id,
            }
            session.save()

        seen_requests: list[tuple[object, str, str]] = []

        def fake_begin(*, user):
            current_request = allauth_context.request
            pending = current_request.session[SESSION_KEY_ADMIN_MFA_PENDING]
            seen_requests.append(
                (current_request, pending["user_pk"], pending["flow_id"])
            )
            current_request.session[allauth_webauthn.STATE_SESSION_KEY] = {
                "challenge": "Y2hhbGxlbmdl",
                "user_verification": "preferred",
            }
            return {"publicKey": {"challenge": "Y2hhbGxlbmdl"}}

        with patch.object(
            allauth_webauthn,
            "begin_authentication",
            side_effect=fake_begin,
        ):
            responses = [
                client.get(
                    "/admin/mfa-verify/webauthn-options/",
                    HTTP_HOST="admin.localhost",
                )
                for client in (self.client, second_client, self.client)
            ]

        self.assertTrue(
            all(response.status_code == 200 for response in responses)
        )
        self.assertEqual(
            [(user_pk, flow_id) for _, user_pk, flow_id in seen_requests],
            [
                (str(first_user.pk), "a" * 32),
                (str(second_user.pk), "b" * 32),
                (str(first_user.pk), "a" * 32),
            ],
        )
        self.assertIsNot(seen_requests[0][0], seen_requests[1][0])
        self.assertIsNot(seen_requests[1][0], seen_requests[2][0])
        self.assertTrue(
            all(
                request.get_host() == "admin.localhost"
                for request, _, _ in seen_requests
            )
        )
        self.assertNotIn("request", allauth_context.__dict__)
        self.assertTrue(
            all(
                "no-store" in response["Cache-Control"]
                for response in responses
            )
        )

    def test_parallel_helpers_keep_allauth_context_isolated(self):
        first_user = self._staff("parallel_context_first")
        second_user = self._staff("parallel_context_second")
        self._activate_totp(first_user)
        self._activate_totp(second_user)
        first_request = self._request(method="get")
        second_request = self._request(method="get")
        first_pending = self._pending_for(first_request, first_user)
        second_pending = self._pending_for(second_request, second_user)
        barrier = Barrier(2)
        seen: dict[int, object] = {}

        def fake_begin(*, user):
            barrier.wait(timeout=5)
            current_request = allauth_context.request
            seen[user.pk] = current_request
            current_request.session[allauth_webauthn.STATE_SESSION_KEY] = {
                "challenge": "Y2hhbGxlbmdl",
                "user_verification": "preferred",
            }
            return {"publicKey": {"challenge": "Y2hhbGxlbmdl"}}

        def run(request, pending):
            with allauth_context.request_context(request):
                return begin_admin_webauthn(request, pending)

        with (
            patch(
                "accounts.services.admin_mfa.admin_user_has_webauthn",
                return_value=True,
            ),
            patch(
                "accounts.services.admin_mfa._is_rate_limited",
                return_value=False,
            ),
            patch.object(
                allauth_webauthn,
                "begin_authentication",
                side_effect=fake_begin,
            ),
            ThreadPoolExecutor(max_workers=2) as executor,
        ):
            first_future = executor.submit(
                run,
                first_request,
                first_pending,
            )
            second_future = executor.submit(
                run,
                second_request,
                second_pending,
            )
            first_options = first_future.result(timeout=10)
            second_options = second_future.result(timeout=10)

        self.assertEqual(
            first_options["publicKey"]["userVerification"],
            "required",
        )
        self.assertEqual(
            second_options["publicKey"]["userVerification"],
            "required",
        )
        self.assertIs(seen[first_user.pk], first_request)
        self.assertIs(seen[second_user.pk], second_request)
        self.assertNotIn("request", allauth_context.__dict__)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "test_admin_mfa_cache",
        },
        "ratelimit": {
            "BACKEND": "backend.cache_backends.FailClosedDatabaseCache",
            "LOCATION": "test_admin_mfa_ratelimit_cache",
            "OPTIONS": {"MAX_ENTRIES": 1000},
        },
        "webauthn_replay": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-admin-mfa-replay",
        },
    },
    RATELIMIT_USE_CACHE="ratelimit",
    ACCOUNT_RATE_LIMITS={"login_failed": "1/m/key"},
    ADMIN_MFA_COMPLETION_RATE="10/m",
    WEBAUTHN_ADMIN_ORIGINS=("http://admin.localhost",),
)
class AdminMFADatabaseCacheTests(TransactionTestCase):
    """Production DatabaseCache counters must survive validation failures."""

    def setUp(self) -> None:
        call_command(
            "createcachetable",
            "test_admin_mfa_cache",
            verbosity=0,
        )
        call_command(
            "createcachetable",
            "test_admin_mfa_ratelimit_cache",
            verbosity=0,
        )
        for backend in caches.all():
            backend.clear()

    def test_allauth_failed_attempt_commits_before_service_raises(self):
        user = User.objects.create_user(
            username="database_cache_counter",
            email="database-cache-counter@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        TOTP.activate(user, TOTP_SECRET)
        request = RequestFactory().post(
            "/admin/mfa-verify/",
            HTTP_HOST="admin.localhost",
            REMOTE_ADDR="203.0.113.10",
        )
        SessionMiddleware(lambda _request: None).process_request(request)
        request.session.save()
        request.user = AnonymousUser()
        pending = start_pending_admin_login(
            request,
            user,
            next_url="/admin/",
        )

        with allauth_context.request_context(request):
            with self.assertRaises(AdminMFAVerificationError):
                verify_admin_code(request, pending, "wrong")
            with self.assertRaises(AdminMFARateLimitError) as raised:
                verify_admin_code(request, pending, "wrong-again")

        self.assertEqual(
            raised.exception.reason_code,
            "allauth_rate_limited",
        )
