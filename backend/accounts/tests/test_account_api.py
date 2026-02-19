from __future__ import annotations

from unittest.mock import patch

from accounts.tests.base import APITestCase
from allauth.account.models import EmailAddress
from allauth.usersessions.models import UserSession
from core.models import UserProfile
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()


class AccountApiTests(APITestCase):
    def create_authenticated_user(self):
        payload = self.signup_and_auth()
        user = User.objects.get(username=payload["username"])
        return user, payload["session_token"]

    def _ensure_current_session_key(self) -> str:
        session = self.client.session
        if not session.session_key:
            session["test"] = "1"
            session.save()
        return session.session_key

    def _prepare_sessions(self, user: User):
        current_key = self._ensure_current_session_key()
        UserSession.objects.get_or_create(
            user=user,
            session_key=current_key,
            defaults={"ip": "127.0.0.1", "user_agent": "current"},
        )

        other_store = SessionStore()
        other_store["uid"] = user.pk
        other_store.save()
        other_key = other_store.session_key
        UserSession.objects.create(
            user=user,
            session_key=other_key,
            ip="127.0.0.2",
            user_agent="other",
        )
        return current_key, other_key

    def test_profile_patch_success_completes_personalization(self):
        user, token = self.create_authenticated_user()

        response = self.patch_json(
            "/account/profile",
            {
                "first_name": "Ivan",
                "last_name": "Ivanov",
                "vk_username": "https://vk.com/id12345",
                "minecraft_nick": "MineCraft_1",
                "minecraft_has_license": True,
                "is_itmo_student": True,
                "itmo_isu": "1234567",
            },
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["ok"], True)
        self.assertEqual(data["profile_state"], "personalized")
        self.assertEqual(data["missing_fields"], [])

        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.vk_username, "id12345")
        self.assertEqual(profile.minecraft_nick, "MineCraft_1")
        self.assertEqual(profile.minecraft_has_license, True)
        self.assertEqual(profile.is_itmo_student, True)
        self.assertEqual(profile.itmo_isu, "1234567")
        self.assertIsNotNone(profile.completed_at)

    def test_profile_patch_invalid_minecraft_nick_returns_field_error(self):
        _, token = self.create_authenticated_user()
        response = self.patch_json(
            "/account/profile",
            {
                "vk_username": "valid_vk",
                "minecraft_nick": "x",
                "minecraft_has_license": True,
                "is_itmo_student": False,
            },
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 400, response.content)
        data = response.json()
        self.assertEqual(data["detail"], "validation_error")
        self.assertIn("minecraft_nick", data["fields"])

    def test_profile_patch_clears_itmo_isu_for_non_itmo(self):
        user, token = self.create_authenticated_user()
        first = self.patch_json(
            "/account/profile",
            {
                "vk_username": "test_vk",
                "minecraft_nick": "Player123",
                "minecraft_has_license": True,
                "is_itmo_student": True,
                "itmo_isu": "7654321",
            },
            **self.auth_headers(token),
        )
        self.assertEqual(first.status_code, 200, first.content)

        second = self.patch_json(
            "/account/profile",
            {"is_itmo_student": False, "itmo_isu": "9999999"},
            **self.auth_headers(token),
        )
        self.assertEqual(second.status_code, 200, second.content)
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.is_itmo_student, False)
        self.assertIsNone(profile.itmo_isu)

    def test_account_delete_requires_correct_password(self):
        user, token = self.create_authenticated_user()
        response = self.post_json(
            "/account/delete",
            {"current_password": "WrongPass123!"},
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertTrue(User.objects.filter(pk=user.pk).exists())

    def test_account_delete_success_removes_user(self):
        user, token = self.create_authenticated_user()
        response = self.post_json(
            "/account/delete",
            {"current_password": self.default_password},
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(User.objects.filter(pk=user.pk).exists())

    def test_account_delete_requires_current_password_field(self):
        _, token = self.create_authenticated_user()
        response = self.post_json(
            "/account/delete",
            {},
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 422, response.content)

    def test_account_delete_success_invalidates_current_session(self):
        _, token = self.create_authenticated_user()
        me_before = self.client.get(
            self.api("/auth/me"),
            **self.auth_headers(token),
        )
        self.assertEqual(me_before.status_code, 200, me_before.content)

        response = self.post_json(
            "/account/delete",
            {"current_password": self.default_password},
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.content)

        me_after = self.client.get(
            self.api("/auth/me"),
            **self.auth_headers(token),
        )
        self.assertEqual(me_after.status_code, 401, me_after.content)

    def test_protected_post_endpoints_require_authentication(self):
        cases = (
            ("/account/delete", {"current_password": self.default_password}),
            ("/account/email/change", {"new_email": self.unique_email("new")}),
            ("/account/email/resend", {}),
            (
                "/account/sessions/bulk",
                {"all_except_current": True, "reason": "manual"},
            ),
            (
                "/account/sessions/_bulk",
                {"all_except_current": True, "reason": "manual"},
            ),
        )
        for path, payload in cases:
            with self.subTest(path=path):
                response = self.post_json(path, payload)
                self.assertEqual(response.status_code, 401, response.content)

    def test_profile_patch_requires_authentication(self):
        response = self.patch_json(
            "/account/profile",
            {"vk_username": "id12345"},
        )
        self.assertEqual(response.status_code, 401, response.content)

    def test_avatar_upload_returns_ok_for_user_without_avatar_field(self):
        _, token = self.create_authenticated_user()
        avatar = SimpleUploadedFile(
            "avatar.png", b"fake-image", content_type="image/png"
        )
        response = self.client.post(
            self.api("/account/avatar"),
            data={"avatar": avatar},
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["ok"], True)

    def test_avatar_upload_requires_authentication(self):
        avatar = SimpleUploadedFile(
            "avatar.png", b"fake-image", content_type="image/png"
        )
        response = self.client.post(
            self.api("/account/avatar"),
            data={"avatar": avatar},
        )
        self.assertEqual(response.status_code, 401, response.content)

    def test_avatar_upload_requires_file_field(self):
        _, token = self.create_authenticated_user()
        response = self.client.post(
            self.api("/account/avatar"),
            data={},
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 422, response.content)

    def test_email_change_requires_new_email_field(self):
        _, token = self.create_authenticated_user()
        response = self.post_json(
            "/account/email/change",
            {},
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 422, response.content)

    def test_email_status_requires_authentication(self):
        response = self.client.get(self.api("/account/email"))
        self.assertEqual(response.status_code, 401, response.content)

    def test_email_status_returns_email_and_verification_state(self):
        user, token = self.create_authenticated_user()
        response = self.client.get(
            self.api("/account/email"),
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["email"], user.email)
        self.assertIsInstance(data["verified"], bool)

    def test_email_change_invalid_email_returns_400(self):
        _, token = self.create_authenticated_user()
        response = self.post_json(
            "/account/email/change",
            {"new_email": "bad-email"},
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(response.json()["detail"], "Invalid email")

    @patch("allauth.account.models.EmailAddress.send_confirmation")
    def test_email_change_same_email_is_idempotent(
        self, send_confirmation_mock
    ):
        user, token = self.create_authenticated_user()
        response = self.post_json(
            "/account/email/change",
            {"new_email": user.email},
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        send_confirmation_mock.assert_not_called()

    @patch("allauth.account.models.EmailAddress.send_confirmation")
    def test_email_change_new_email_sends_confirmation(
        self, send_confirmation_mock
    ):
        user, token = self.create_authenticated_user()
        new_email = self.unique_email("change")
        response = self.post_json(
            "/account/email/change",
            {"new_email": new_email},
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        send_confirmation_mock.assert_called_once()
        self.assertTrue(
            EmailAddress.objects.filter(user=user, email=new_email).exists()
        )

    @patch("allauth.account.models.EmailAddress.send_confirmation")
    def test_email_resend_sends_for_unverified_email(
        self, send_confirmation_mock
    ):
        user, token = self.create_authenticated_user()
        EmailAddress.objects.update_or_create(
            user=user,
            email=user.email,
            defaults={"primary": True, "verified": False},
        )

        response = self.post_json(
            "/account/email/resend",
            {},
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        send_confirmation_mock.assert_called_once()

    @patch("allauth.account.models.EmailAddress.send_confirmation")
    def test_email_resend_noop_when_all_emails_verified(
        self, send_confirmation_mock
    ):
        user, token = self.create_authenticated_user()
        EmailAddress.objects.update_or_create(
            user=user,
            email=user.email,
            defaults={"primary": True, "verified": True},
        )
        EmailAddress.objects.filter(user=user, verified=False).delete()

        response = self.post_json(
            "/account/email/resend",
            {},
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        send_confirmation_mock.assert_not_called()

    def test_sessions_bulk_post_revokes_all_except_current(self):
        user, token = self.create_authenticated_user()
        _, other_key = self._prepare_sessions(user)

        response = self.post_json(
            "/account/sessions/bulk",
            {"all_except_current": True, "reason": "manual"},
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["ok"], True)
        self.assertIn(other_key, data["revoked_ids"])

        store = SessionStore(session_key=other_key)
        self.assertFalse(store.exists(other_key))

    def test_sessions_list_requires_authentication(self):
        response = self.client.get(self.api("/account/sessions"))
        self.assertEqual(response.status_code, 401, response.content)

    def test_sessions_list_returns_current_and_other_sessions(self):
        user, token = self.create_authenticated_user()
        current_key, other_key = self._prepare_sessions(user)
        response = self.client.get(
            self.api("/account/sessions"),
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        sessions = response.json()["sessions"]
        ids = {row["id"] for row in sessions}
        self.assertIn(current_key, ids)
        self.assertIn(other_key, ids)
        current_row = next(
            (row for row in sessions if row["id"] == current_key),
            None,
        )
        self.assertIsNotNone(current_row)
        self.assertEqual(current_row["current"], True)

    def test_sessions_bulk_without_scope_returns_400(self):
        _, token = self.create_authenticated_user()
        response = self.post_json(
            "/account/sessions/bulk",
            {},
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test_sessions_bulk_rejects_conflicting_scope(self):
        user, token = self.create_authenticated_user()
        _, other_key = self._prepare_sessions(user)
        response = self.post_json(
            "/account/sessions/bulk",
            {"ids": [other_key], "all_except_current": True},
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test_sessions_bulk_compat_endpoint_revokes_all_except_current(self):
        user, token = self.create_authenticated_user()
        _, other_key = self._prepare_sessions(user)

        response = self.post_json(
            "/account/sessions/_bulk",
            {"all_except_current": True, "reason": "manual"},
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn(other_key, response.json()["revoked_ids"])

    def test_sessions_bulk_compat_without_scope_returns_400(self):
        _, token = self.create_authenticated_user()
        response = self.post_json(
            "/account/sessions/_bulk",
            {},
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test_revoke_single_session_requires_authentication(self):
        response = self.client.delete(
            self.api("/account/sessions/nonexistent")
        )
        self.assertEqual(response.status_code, 401, response.content)

    def test_revoke_single_session_returns_404_for_unknown_sid(self):
        _, token = self.create_authenticated_user()
        response = self.client.delete(
            self.api("/account/sessions/not_found"),
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 404, response.content)

    def test_revoke_single_session_success(self):
        user, token = self.create_authenticated_user()
        _, other_key = self._prepare_sessions(user)

        response = self.client.delete(
            self.api(f"/account/sessions/{other_key}"),
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["ok"], True)
        self.assertEqual(data["id"], other_key)

        store = SessionStore(session_key=other_key)
        self.assertFalse(store.exists(other_key))

        list_response = self.client.get(
            self.api("/account/sessions"),
            **self.auth_headers(token),
        )
        self.assertEqual(list_response.status_code, 200, list_response.content)
        rows = list_response.json()["sessions"]
        revoked = next((row for row in rows if row["id"] == other_key), None)
        self.assertIsNotNone(revoked)
        self.assertEqual(revoked["revoked"], True)
