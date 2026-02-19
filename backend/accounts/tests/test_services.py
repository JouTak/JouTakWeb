from __future__ import annotations

from accounts.services.account_status import AccountStatusService
from accounts.services.personalization import (
    missing_personalization_fields,
    personalization_complete,
)
from accounts.services.profile import ProfileService
from accounts.services.sessions import SessionService
from core.models import UserProfile, UserSessionMeta
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from ninja.errors import HttpError

User = get_user_model()


class PersonalizationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="svc_user",
            email="svc_user@example.com",
            password="StrongPass123!",
        )

    def test_missing_fields_for_empty_profile(self):
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

    def test_personalization_complete_for_itmo_student(self):
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
    def setUp(self):
        self.user = User.objects.create_user(
            username="profile_user",
            email="profile_user@example.com",
            password="StrongPass123!",
        )

    def test_normalize_vk_username(self):
        normalized = ProfileService.normalize_vk_username(
            " https://vk.com/@my.user/ "
        )
        self.assertEqual(normalized, "my.user")

    def test_update_profile_fields_raises_for_invalid_minecraft_nick(self):
        with self.assertRaises(HttpError) as ctx:
            ProfileService.update_profile_fields(
                self.user,
                vk_username="valid_vk",
                minecraft_nick="x",
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("minecraft_nick", str(ctx.exception.message))

    def test_update_profile_fields_sets_completed_at(self):
        profile = ProfileService.update_profile_fields(
            self.user,
            vk_username="valid_vk",
            minecraft_nick="Player123",
            minecraft_has_license=True,
            is_itmo_student=False,
            itmo_isu="",
        )
        self.assertIsNotNone(profile.completed_at)


class AccountStatusServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="status_user",
            email="status_user@example.com",
            password="StrongPass123!",
        )
        self.profile = UserProfile.objects.create(user=self.user)

    @override_settings(FF_PROFILE_PERSONALIZATION_ENFORCE=True)
    def test_require_personalized_profile_raises_for_incomplete(self):
        with self.assertRaises(HttpError) as ctx:
            AccountStatusService.require_personalized_profile(self.user)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn(
            "PROFILE_PERSONALIZATION_REQUIRED",
            str(ctx.exception.message),
        )

    @override_settings(FF_PROFILE_PERSONALIZATION_ENFORCE=True)
    def test_require_personalized_profile_passes_for_complete(self):
        self.profile.vk_username = "id77"
        self.profile.minecraft_nick = "Mine777"
        self.profile.minecraft_has_license = True
        self.profile.is_itmo_student = False
        self.profile.save()
        AccountStatusService.require_personalized_profile(self.user)


class SessionServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="session_user",
            email="session_user@example.com",
            password="StrongPass123!",
        )
        self.factory = RequestFactory()

    def _request_with_session(self, token: str):
        request = self.factory.get(
            "/api/account/sessions", HTTP_X_SESSION_TOKEN=token
        )
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        return request

    def test_assert_session_allowed_raises_when_session_revoked(self):
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
