from __future__ import annotations

from importlib import import_module
from unittest.mock import patch

from accounts.adapters import StrictAccountAdapter
from accounts.mfa_adapter import EncryptedMFAAdapter
from accounts.services.account_status import AccountStatusService
from accounts.services.email_addresses import sync_user_email_address
from accounts.services.personalization import (
    missing_personalization_fields,
    personalization_complete,
)
from accounts.services.profile import ProfileService
from accounts.services.sessions import SessionService
from accounts.token_strategy import RevocableSessionTokenStrategy
from allauth.account.models import EmailAddress
from core.models import UserProfile, UserSessionMeta
from django.conf import settings
from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.db import connection
from django.http import HttpRequest
from django.test import (
    RequestFactory,
    TestCase,
    TransactionTestCase,
    override_settings,
)
from django.utils import timezone
from ninja.errors import HttpError

User = get_user_model()
TEST_PASSWORD = "StrongPass123!"


class PersonalizationServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="svc_user",
            email="svc_user@example.com",
            password=TEST_PASSWORD,
        )

    def test_missing_fields_for_empty_profile(self) -> None:
        profile = UserProfile.objects.create(user=self.user)
        missing = missing_personalization_fields(profile)
        self.assertEqual(
            set(missing),
            {
                "vk_username",
                "minecraft_nick",
                "minecraft_has_license",
                "is_itmo_student",
            },
        )

    def test_personalization_complete_for_itmo_student(self) -> None:
        profile = UserProfile.objects.create(
            user=self.user,
            vk_username="id42",
            minecraft_nick="Mine42_",
            minecraft_has_license=True,
            is_itmo_student=True,
            itmo_isu="123456",
        )
        complete, missing = personalization_complete(profile)
        self.assertTrue(complete)
        self.assertEqual(missing, [])


class ProfileServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="profile_user",
            email="profile_user@example.com",
            password=TEST_PASSWORD,
        )

    def test_normalize_vk_username(self) -> None:
        normalized = ProfileService.normalize_vk_username(
            " https://vk.com/@my.user/ "
        )
        self.assertEqual(normalized, "my.user")

    def test_update_profile_fields_raises_for_invalid_minecraft_nick(
        self,
    ) -> None:
        with self.assertRaises(HttpError) as ctx:
            ProfileService.update_profile_fields(
                self.user,
                vk_username="valid_vk",
                minecraft_nick="x",
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("minecraft_nick", str(ctx.exception.message))

    def test_update_profile_fields_sets_completed_at(self) -> None:
        profile = ProfileService.update_profile_fields(
            self.user,
            vk_username="valid_vk",
            minecraft_nick="Player123",
            minecraft_has_license=True,
            is_itmo_student=False,
            itmo_isu="",
        )
        self.assertIsNotNone(profile.completed_at)

    def test_update_profile_fields_rejects_overlong_first_name(self) -> None:
        max_length = self.user._meta.get_field("first_name").max_length or 1
        with self.assertRaises(HttpError) as ctx:
            ProfileService.update_profile_fields(
                self.user,
                first_name="x" * (max_length + 1),
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("first_name", str(ctx.exception.message))


class AccountStatusServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="status_user",
            email="status_user@example.com",
            password=TEST_PASSWORD,
        )
        self.profile = UserProfile.objects.create(user=self.user)

    @override_settings(FF_PROFILE_PERSONALIZATION_ENFORCE=True)
    def test_require_personalized_profile_raises_for_incomplete(self) -> None:
        with self.assertRaises(HttpError) as ctx:
            AccountStatusService.require_personalized_profile(self.user)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn(
            "PROFILE_PERSONALIZATION_REQUIRED",
            str(ctx.exception.message),
        )

    @override_settings(FF_PROFILE_PERSONALIZATION_ENFORCE=True)
    def test_require_personalized_profile_passes_for_complete(self) -> None:
        self.profile.vk_username = "id77"
        self.profile.minecraft_nick = "Mine777"
        self.profile.minecraft_has_license = True
        self.profile.is_itmo_student = False
        self.profile.save()
        AccountStatusService.require_personalized_profile(self.user)


class EmailAddressServiceTests(TestCase):
    def test_sync_user_email_address_creates_primary_email_address(
        self,
    ) -> None:
        user = User.objects.create_user(
            username="email_service_user",
            email="Email.Service@Example.com",
            password=TEST_PASSWORD,
        )

        result = sync_user_email_address(user)

        address = EmailAddress.objects.get(user=user)
        self.assertTrue(result.created)
        self.assertTrue(result.promoted_primary)
        self.assertEqual(address.email, "email.service@example.com")
        self.assertTrue(address.primary)
        self.assertFalse(address.verified)

    def test_sync_user_email_address_promotes_updated_user_email(self) -> None:
        user = User.objects.create_user(
            username="email_service_switch",
            email="old@example.com",
            password=TEST_PASSWORD,
        )
        old_address = EmailAddress.objects.add_email(
            request=None,
            user=user,
            email="old@example.com",
            confirm=False,
        )
        old_address.set_as_primary()

        user.email = "new@example.com"
        user.save(update_fields=["email"])

        result = sync_user_email_address(user)

        old_address.refresh_from_db()
        new_address = EmailAddress.objects.get(
            user=user,
            email="new@example.com",
        )
        user.refresh_from_db()
        self.assertTrue(result.created)
        self.assertTrue(result.promoted_primary)
        self.assertFalse(old_address.primary)
        self.assertTrue(new_address.primary)
        self.assertEqual(user.email, "new@example.com")


class SessionServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="session_user",
            email="session_user@example.com",
            password=TEST_PASSWORD,
        )
        self.factory = RequestFactory()

    def _request_with_session(self, token: str) -> HttpRequest:
        request = self.factory.get(
            "/api/account/sessions", HTTP_X_SESSION_TOKEN=token
        )
        middleware = SessionMiddleware(lambda _request: None)
        middleware.process_request(request)
        request.session.save()
        return request

    def test_assert_session_allowed_raises_when_session_revoked(self) -> None:
        token = "session_token_1"
        UserSessionMeta.objects.create(
            user=self.user,
            session_key="k1",
            session_token=token,
            revoked_reason="manual",
            revoked_at=timezone.now(),
        )
        request = self._request_with_session(token)

        with self.assertRaises(HttpError) as ctx:
            SessionService.assert_session_allowed(request)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.message, "session revoked")


class RevocableSessionTokenStrategyTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="token_strategy_user",
            email="token_strategy_user@example.com",
            password=TEST_PASSWORD,
        )
        self.strategy = RevocableSessionTokenStrategy()

    def _create_session(self) -> str:
        engine = import_module(settings.SESSION_ENGINE)
        session = engine.SessionStore()
        session[SESSION_KEY] = str(self.user.pk)
        session.save()
        return session.session_key or ""

    def test_lookup_session_rejects_revoked_meta_by_session_token(
        self,
    ) -> None:
        session_token = self._create_session()
        UserSessionMeta.objects.create(
            user=self.user,
            session_key="different-session-key",
            session_token=session_token,
            revoked_reason="manual",
            revoked_at=timezone.now(),
        )

        self.assertIsNone(self.strategy.lookup_session(session_token))


class StrictAccountAdapterTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.adapter = StrictAccountAdapter()

    @override_settings(
        ACCOUNT_TRUST_PROXY_HEADERS=True,
        ACCOUNT_TRUSTED_PROXY_CIDRS=("10.0.0.0/8",),
    )
    def test_get_client_ip_prefers_proxy_overwritten_x_real_ip(self) -> None:
        request = self.factory.get(
            "/login",
            REMOTE_ADDR="10.1.2.3",
            HTTP_X_REAL_IP="203.0.113.42",
            HTTP_X_FORWARDED_FOR="198.51.100.1, 203.0.113.42",
        )

        self.assertEqual(self.adapter.get_client_ip(request), "203.0.113.42")

    @override_settings(
        ACCOUNT_TRUST_PROXY_HEADERS=True,
        ACCOUNT_TRUSTED_PROXY_CIDRS=("10.0.0.0/8",),
    )
    def test_get_client_ip_uses_rightmost_untrusted_forwarded_ip(self) -> None:
        request = self.factory.get(
            "/login",
            REMOTE_ADDR="10.1.2.3",
            HTTP_X_FORWARDED_FOR="198.51.100.7, 203.0.113.9",
        )

        self.assertEqual(self.adapter.get_client_ip(request), "203.0.113.9")


class EncryptedMFAAdapterTests(TestCase):
    @override_settings(SECRET_KEY="legacy-secret-key")
    def test_decrypts_legacy_secret_after_dedicated_key_is_added(self) -> None:
        legacy_adapter = EncryptedMFAAdapter()
        ciphertext = legacy_adapter.encrypt("otp-secret")

        with override_settings(
            SECRET_KEY="legacy-secret-key",
            MFA_ENCRYPTION_KEYS=("new-dedicated-key",),
            MFA_ENCRYPTION_INCLUDE_LEGACY_SECRET_KEY=True,
        ):
            rotated_adapter = EncryptedMFAAdapter()
            self.assertEqual(rotated_adapter.decrypt(ciphertext), "otp-secret")


class SessionServiceTransactionTests(TransactionTestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="session_tx_user",
            email="session_tx_user@example.com",
            password=TEST_PASSWORD,
        )
        self.factory = RequestFactory()

    def _request_with_session(self, token: str) -> HttpRequest:
        request = self.factory.get(
            "/api/account/sessions", HTTP_X_SESSION_TOKEN=token
        )
        middleware = SessionMiddleware(lambda _request: None)
        middleware.process_request(request)
        request.session.save()
        return request

    def test_touch_runs_inside_atomic_block(self) -> None:
        self.assertFalse(connection.in_atomic_block)
        request = self._request_with_session("session_token_tx_1")
        observed: dict[str, bool] = {}
        original = SessionService._resolve_meta_for_touch

        def wrapped(user: User, token: str, dj_key: str) -> UserSessionMeta:
            observed["in_atomic"] = connection.in_atomic_block
            return original(user, token, dj_key)

        with patch.object(
            SessionService,
            "_resolve_meta_for_touch",
            side_effect=wrapped,
        ):
            SessionService.touch(request, self.user)
        self.assertTrue(observed.get("in_atomic", False))
