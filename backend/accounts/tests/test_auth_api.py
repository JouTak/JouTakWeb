from __future__ import annotations

from accounts.tests.base import APITestCase
from core.models import UserSessionMeta, UserSessionToken
from django.contrib.auth import get_user_model
from ninja_jwt.tokens import RefreshToken

User = get_user_model()


class HeadlessAuthApiTests(APITestCase):
    def jwt_from_session(self, session_token: str):
        return self.post_json(
            "/auth/jwt/from_session",
            {},
            **self.auth_headers(session_token),
        )

    def test_signup_success_returns_session_token_in_header_and_body(self):
        username = self.unique_username("signup")
        email = self.unique_email("signup")

        response = self.signup(username=username, email=email)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            response.headers.get("Cache-Control"),
            "no-store",
        )
        token = self.session_token(response)
        self.assertTrue(token)
        self.assertEqual(response.json()["meta"]["session_token"], token)
        self.assertTrue(User.objects.filter(username=username).exists())

    def test_signup_invalid_returns_structured_validation_error(self):
        response = self.signup(
            username=self.unique_username("bad"),
            email=self.unique_email("bad"),
            password="123",
        )

        self.assertEqual(response.status_code, 400, response.content)
        data = response.json()
        self.assertEqual(data["detail"], "validation_error")
        self.assertIn("password1", data["fields"])

    def test_login_success_and_invalid_credentials(self):
        username = self.unique_username("login")
        password = self.default_password
        self.signup(
            username=username,
            email=self.unique_email("login"),
            password=password,
        )

        ok = self.login(username=username, password=password)
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertTrue(self.session_token(ok))

        bad = self.login(username=username, password="WrongPass123!")
        self.assertEqual(bad.status_code, 400, bad.content)
        self.assertEqual(bad.json()["detail"], "invalid credentials")

    def test_jwt_from_session_requires_authentication(self):
        response = self.post_json("/auth/jwt/from_session", {})
        self.assertEqual(response.status_code, 401, response.content)

    def test_logout_requires_authentication(self):
        response = self.post_json("/auth/logout", {})
        self.assertEqual(response.status_code, 401, response.content)

    def test_change_password_requires_authentication(self):
        response = self.post_json(
            "/auth/change_password",
            {
                "current_password": "OldPass123!",
                "new_password": "NewPass123!",
            },
        )
        self.assertEqual(response.status_code, 401, response.content)

    def test_login_rejects_missing_required_fields(self):
        response = self.post_json("/auth/login", {})
        self.assertEqual(response.status_code, 422, response.content)

    def test_signup_rejects_missing_required_fields(self):
        response = self.post_json("/auth/signup", {"username": "missing_pass"})
        self.assertEqual(response.status_code, 422, response.content)

    def test_refresh_rejects_missing_required_fields(self):
        response = self.post_json("/auth/refresh", {})
        self.assertEqual(response.status_code, 422, response.content)

    def test_jwt_from_session_creates_session_meta_and_refresh_mapping(self):
        payload = self.signup_and_auth()
        username = payload["username"]
        session_token = payload["session_token"]

        response = self.jwt_from_session(session_token)
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        self.assertTrue(data.get("access"))
        self.assertTrue(data.get("refresh"))

        user = User.objects.get(username=username)
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

    def test_auth_me_and_logout_invalidate_session(self):
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

    def test_change_password_post_conditions(self):
        username = self.unique_username("pwd")
        old_password = "OldStrongPass123!"
        new_password = "NewStrongPass456!"

        signup = self.signup(
            username=username,
            email=self.unique_email("pwd"),
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
        self.assertEqual(
            wrong_current.json()["detail"], "wrong current password"
        )

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

        old_login = self.login(username=username, password=old_password)
        self.assertEqual(old_login.status_code, 400, old_login.content)

        new_login = self.login(username=username, password=new_password)
        self.assertEqual(new_login.status_code, 200, new_login.content)

    def test_refresh_rejects_invalid_refresh(self):
        response = self.post_json(
            "/auth/refresh", {"refresh": "definitely-invalid-token"}
        )
        self.assertEqual(response.status_code, 401, response.content)
        self.assertEqual(response.json()["detail"], "invalid refresh")

    def test_refresh_rotates_and_blacklists_old_refresh(self):
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
            "/auth/refresh", {"refresh": new_refresh}
        )
        self.assertEqual(
            third_refresh_with_new.status_code,
            200,
            third_refresh_with_new.content,
        )

    def test_refresh_updates_existing_session_refresh_mapping(self):
        payload = self.signup_and_auth()
        username = payload["username"]
        session_token = payload["session_token"]

        pair = self.jwt_from_session(session_token).json()
        refresh_1 = pair["refresh"]
        jti_1 = str(RefreshToken(refresh_1).get("jti"))
        user = User.objects.get(username=username)
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
