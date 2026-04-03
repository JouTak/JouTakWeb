from __future__ import annotations

from accounts.tests.base import APITestCase
from core.models import UserSessionMeta, UserSessionToken
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken

User = get_user_model()


class HeadlessAuthApiTests(APITestCase):
    def jwt_from_session(self, session_token: str) -> HttpResponse:
        return self.post_json(
            "/auth/jwt/from_session",
            {},
            **self.auth_headers(session_token),
        )

    def _revoke_token(self, user: User, token: str) -> None:
        UserSessionMeta.objects.update_or_create(
            user=user,
            session_key=token,
            defaults={
                "session_token": token,
                "revoked_reason": "manual",
                "revoked_at": timezone.now(),
            },
        )

    def test_signup_success_returns_session_token_and_generates_username(
        self,
    ) -> None:
        email = self.unique_email("signup")

        response = self.signup(email=email)

        self.assertEqual(response.status_code, 200, response.content)
        token = self.session_token(response)
        self.assertTrue(token)
        self.assertEqual(response.json()["meta"]["session_token"], token)

        user = User.objects.get(email=email.lower())
        self.assertTrue(user.username)

    def test_signup_invalid_returns_structured_validation_error(self) -> None:
        weak_password = "123"
        response = self.signup(
            email=self.unique_email("bad"),
            password=weak_password,
        )

        self.assertEqual(response.status_code, 400, response.content)
        data = response.json()
        self.assertTrue(data.get("errors"))

    def test_login_success_and_invalid_credentials_by_email(self) -> None:
        email = self.unique_email("login")
        password = self.default_password
        self.signup(
            email=email,
            password=password,
        )

        ok = self.login(email=email, password=password)
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertTrue(self.session_token(ok))

        wrong_password = "WrongPass123!"
        bad = self.login(email=email, password=wrong_password)
        self.assertEqual(bad.status_code, 400, bad.content)
        self.assertTrue(bad.json().get("errors"))

    def test_login_rejects_legacy_username_field(self) -> None:
        email = self.unique_email("legacy_field")
        self.signup(email=email, password=self.default_password)

        response = self.headless_post_json(
            "/auth/login",
            {
                "username": email.split("@")[0],
                "password": self.default_password,
            },
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test_jwt_from_session_requires_authentication(self) -> None:
        response = self.post_json("/auth/jwt/from_session", {})
        self.assertEqual(response.status_code, 401, response.content)

    def test_jwt_from_session_rejects_revoked_session_token(self) -> None:
        payload = self.signup_and_auth()
        user = User.objects.get(email=payload["email"].lower())
        token = payload["session_token"]
        self._revoke_token(user, token)
        response = self.jwt_from_session(token)
        self.assertEqual(response.status_code, 401, response.content)

    def test_logout_requires_authentication(self) -> None:
        response = self.post_json("/auth/logout", {})
        self.assertEqual(response.status_code, 401, response.content)

    def test_change_password_requires_authentication(self) -> None:
        response = self.post_json(
            "/auth/change_password",
            {
                "current_password": "OldPass123!",
                "new_password": "NewPass123!",
            },
        )
        self.assertEqual(response.status_code, 401, response.content)

    def test_login_rejects_missing_required_fields(self) -> None:
        response = self.headless_post_json("/auth/login", {})
        self.assertEqual(response.status_code, 400, response.content)
        self.assertTrue(response.json().get("errors"))

    def test_signup_rejects_missing_required_fields(self) -> None:
        response = self.headless_post_json("/auth/signup", {})
        self.assertEqual(response.status_code, 400, response.content)
        self.assertTrue(response.json().get("errors"))

    def test_refresh_rejects_missing_required_fields(self) -> None:
        response = self.post_json("/auth/refresh", {})
        self.assertEqual(response.status_code, 422, response.content)

    def test_jwt_from_session_creates_session_meta_and_refresh_mapping(
        self,
    ) -> None:
        payload = self.signup_and_auth()
        session_token = payload["session_token"]

        response = self.jwt_from_session(session_token)
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        self.assertTrue(data.get("access"))
        self.assertTrue(data.get("refresh"))

        user = User.objects.get(email=payload["email"].lower())
        meta = UserSessionMeta.objects.filter(
            user=user, session_token=session_token
        ).first()
        self.assertIsNotNone(meta)

        refresh_jti = str(RefreshToken(data["refresh"]).get("jti"))
        self.assertTrue(
            UserSessionToken.objects.filter(
                user=user,
                session_key=meta.session_key,
                refresh_jti=refresh_jti,
            ).exists()
        )

    def test_auth_me_and_logout_invalidate_session(self) -> None:
        payload = self.signup_and_auth()
        token = payload["session_token"]

        me_before = self.client.get(
            self.api("/auth/me"), **self.auth_headers(token)
        )
        self.assertEqual(me_before.status_code, 200, me_before.content)

        logout_resp = self.post_json(
            "/auth/logout", {}, **self.auth_headers(token)
        )
        self.assertEqual(logout_resp.status_code, 200, logout_resp.content)

        me_after = self.client.get(
            self.api("/auth/me"), **self.auth_headers(token)
        )
        self.assertEqual(me_after.status_code, 401, me_after.content)

    def test_auth_me_rejects_revoked_session_token(self) -> None:
        payload = self.signup_and_auth()
        user = User.objects.get(email=payload["email"].lower())
        token = payload["session_token"]
        self._revoke_token(user, token)
        response = self.client.get(
            self.api("/auth/me"),
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 401, response.content)

    def test_logout_revokes_current_session_refresh_mapping(self) -> None:
        payload = self.signup_and_auth()
        session_token = payload["session_token"]
        pair = self.jwt_from_session(session_token).json()
        refresh = pair["refresh"]
        refresh_jti = str(RefreshToken(refresh).get("jti"))

        user = User.objects.get(email=payload["email"].lower())
        mapping = UserSessionToken.objects.filter(
            user=user, refresh_jti=refresh_jti
        ).first()
        self.assertIsNotNone(mapping)
        self.assertIsNone(mapping.revoked_at)

        logout_resp = self.post_json(
            "/auth/logout", {}, **self.auth_headers(session_token)
        )
        self.assertEqual(logout_resp.status_code, 200, logout_resp.content)

        mapping.refresh_from_db()
        self.assertIsNotNone(mapping.revoked_at)

        refresh_after_logout = self.post_json(
            "/auth/refresh", {"refresh": refresh}
        )
        self.assertEqual(
            refresh_after_logout.status_code,
            401,
            refresh_after_logout.content,
        )
        self.assertEqual(
            refresh_after_logout.json()["detail"],
            "invalid refresh",
        )

    def test_change_password_post_conditions(self) -> None:
        email = self.unique_email("pwd")
        old_password = "OldStrongPass123!"
        new_password = "NewStrongPass456!"

        signup = self.signup(
            email=email,
            password=old_password,
        )
        session_token = self.session_token(signup)

        wrong_current = self.post_json(
            "/auth/change_password",
            {
                "current_password": "WrongCurrent123!",
                "new_password": new_password,
            },
            **self.auth_headers(session_token),
        )
        self.assertEqual(wrong_current.status_code, 400, wrong_current.content)
        self.assertEqual(wrong_current.json()["detail"], "validation_error")
        self.assertIn("current_password", wrong_current.json()["fields"])

        same_as_current = self.post_json(
            "/auth/change_password",
            {
                "current_password": old_password,
                "new_password": old_password,
            },
            **self.auth_headers(session_token),
        )
        self.assertEqual(
            same_as_current.status_code, 400, same_as_current.content
        )
        self.assertIn(
            "new password must differ from current",
            same_as_current.json()["detail"],
        )

        success = self.post_json(
            "/auth/change_password",
            {
                "current_password": old_password,
                "new_password": new_password,
            },
            **self.auth_headers(session_token),
        )
        self.assertEqual(success.status_code, 200, success.content)
        self.assertEqual(success.json()["ok"], True)
        self.assertEqual(success.json()["terminated_other_sessions"], True)

        old_login = self.login(email=email, password=old_password)
        self.assertEqual(old_login.status_code, 400, old_login.content)

        new_login = self.login(email=email, password=new_password)
        self.assertEqual(new_login.status_code, 200, new_login.content)

    def test_change_password_can_keep_other_sessions(self) -> None:
        email = self.unique_email("pwd_keep_sessions")
        old_password = "OldStrongPass123!"
        new_password = "NewStrongPass456!"

        signup = self.signup(
            email=email,
            password=old_password,
        )
        session_token = self.session_token(signup)

        response = self.post_json(
            "/auth/change_password",
            {
                "current_password": old_password,
                "new_password": new_password,
                "terminate_other_sessions": False,
            },
            **self.auth_headers(session_token),
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["ok"], True)
        self.assertEqual(
            response.json()["terminated_other_sessions"],
            False,
        )

    def test_refresh_rejects_invalid_refresh(self) -> None:
        response = self.post_json(
            "/auth/refresh", {"refresh": "definitely-invalid-token"}
        )
        self.assertEqual(response.status_code, 401, response.content)
        self.assertEqual(response.json()["detail"], "invalid refresh")

    def test_refresh_rotates_and_blacklists_old_refresh(self) -> None:
        payload = self.signup_and_auth()
        session_token = payload["session_token"]
        pair = self.jwt_from_session(session_token).json()
        old_refresh = pair["refresh"]

        first_refresh = self.post_json(
            "/auth/refresh",
            {"refresh": old_refresh},
            **self.auth_headers(session_token),
        )
        self.assertEqual(first_refresh.status_code, 200, first_refresh.content)
        new_refresh = first_refresh.json()["refresh"]
        self.assertNotEqual(new_refresh, old_refresh)

        second_refresh_with_old = self.post_json(
            "/auth/refresh", {"refresh": old_refresh}
        )
        self.assertEqual(
            second_refresh_with_old.status_code,
            401,
            second_refresh_with_old.content,
        )

        third_refresh_with_new = self.post_json(
            "/auth/refresh",
            {"refresh": new_refresh},
            **self.auth_headers(session_token),
        )
        self.assertEqual(
            third_refresh_with_new.status_code,
            200,
            third_refresh_with_new.content,
        )

    def test_refresh_requires_session_token_header(self) -> None:
        payload = self.signup_and_auth()
        session_token = payload["session_token"]
        pair = self.jwt_from_session(session_token).json()
        refresh_token = pair["refresh"]

        response = self.post_json("/auth/refresh", {"refresh": refresh_token})
        self.assertEqual(response.status_code, 401, response.content)
        self.assertEqual(
            response.json()["detail"],
            "session token required for refresh",
        )

    def test_refresh_updates_existing_session_refresh_mapping(self) -> None:
        payload = self.signup_and_auth()
        session_token = payload["session_token"]

        pair = self.jwt_from_session(session_token).json()
        refresh_1 = pair["refresh"]
        jti_1 = str(RefreshToken(refresh_1).get("jti"))
        user = User.objects.get(email=payload["email"].lower())
        mapping = UserSessionToken.objects.filter(
            user=user, refresh_jti=jti_1
        ).first()
        self.assertIsNotNone(mapping)
        session_key = mapping.session_key

        refreshed = self.post_json(
            "/auth/refresh",
            {"refresh": refresh_1},
            **self.auth_headers(session_token),
        )
        self.assertEqual(refreshed.status_code, 200, refreshed.content)
        refresh_2 = refreshed.json()["refresh"]
        jti_2 = str(RefreshToken(refresh_2).get("jti"))

        self.assertFalse(
            UserSessionToken.objects.filter(
                user=user, session_key=session_key, refresh_jti=jti_1
            ).exists()
        )
        self.assertTrue(
            UserSessionToken.objects.filter(
                user=user, session_key=session_key, refresh_jti=jti_2
            ).exists()
        )
