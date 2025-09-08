"""import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

API = "/api"
HEADLESS_APP = "/_allauth/app/v1"
-> /todo с учетом отказа от использования не безопасных ручек либы переписать тесты.

User = get_user_model()


def auth_header(access: str):
    return {"HTTP_AUTHORIZATION": f"Bearer {access}"}


def _extract_session_token(resp):
    try:
        body = json.loads(resp.content)
    except Exception:
        body = {}
    return (body.get("meta") or {}).get("session_token") or resp.headers.get(
        "X-Session-Token"
    )


PW_DENIS = "D3n!s#Pass2025"
PW_IVAN = "Iv@n#Pass2025!"
PW_IVAN_NEW = "Iv@n#Pass2026!"
PW_RENAT = "R3nat#Pa$$2025"


class AuthFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        site, _ = Site.objects.get_or_create(
            id=1, defaults={"domain": "testserver", "name": "testserver"}
        )
        app = SocialApp.objects.create(
            provider="yandex", name="Yandex", client_id="dummy", secret="dummy"
        )
        app.sites.add(site)

    def setUp(self):
        self.c = Client()

    def _signup_session(self, username, email, password):
        payload = {"email": email, "username": username, "password": password}
        resp = self.c.post(
            f"{HEADLESS_APP}/auth/signup",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        token = _extract_session_token(resp)
        self.assertTrue(token, "session_token not returned by signup")
        return token

    def _login_session(self, identifier, password):
        payload = {
            "identifier": identifier,
            "login": identifier,
            "password": password,
        }
        if "@" in identifier:
            payload["email"] = identifier
        else:
            payload["username"] = identifier
        resp = self.c.post(
            f"{HEADLESS_APP}/auth/login",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = json.loads(resp.content)
        token = (body.get("meta") or {}).get(
            "session_token"
        ) or resp.headers.get("X-Session-Token")
        self.assertTrue(token, "session_token not returned by login")
        return token

    def _jwt_from_session(self, session_token: str):
        resp = self.c.post(
            f"{API}/auth/jwt/from_session",
            **{"HTTP_X_SESSION_TOKEN": session_token},
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        data = json.loads(resp.content)
        return data["access"], data["refresh"]

    def test_signup_login_refresh_logout_and_me(self):
        sess = self._signup_session(
            username="Denis", email="denis@joutak.ru", password=PW_DENIS
        )
        access, refresh = self._jwt_from_session(sess)

        resp = self.c.get(f"{API}/auth/me", **auth_header(access))
        self.assertEqual(resp.status_code, 200, resp.content)
        me = json.loads(resp.content)
        self.assertEqual(me["username"], "Denis")
        self.assertEqual(me["has_2fa"], False)

        resp = self.c.post(
            f"{API}/token/refresh",
            data=json.dumps({"refresh": refresh}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        data = json.loads(resp.content)
        new_access = data["access"]
        new_refresh = data.get("refresh")
        self.assertTrue(new_access)
        self.assertTrue(new_refresh)

        resp = self.c.post(
            f"{API}/auth/logout",
            data=json.dumps({"refresh": new_refresh}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        sess2 = self._login_session("denis@joutak.ru", PW_DENIS)
        a2, _ = self._jwt_from_session(sess2)

        resp = self.c.post(f"{API}/auth/logout_all", **auth_header(a2))
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_change_password_and_relogin(self):
        sess = self._signup_session(
            username="Ivan", email="ivan@joutak.ru", password=PW_IVAN
        )
        access, _ = self._jwt_from_session(sess)

        resp = self.c.post(
            f"{API}/auth/change_password",
            data=json.dumps(
                {"current_password": PW_IVAN, "new_password": PW_IVAN_NEW}
            ),
            content_type="application/json",
            **auth_header(access),
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        sess2 = self._login_session("ivan@joutak.ru", PW_IVAN_NEW)
        a2, _ = self._jwt_from_session(sess2)
        self.assertTrue(a2)

    def test_oauth_helpers_yandex(self):
        sess = self._signup_session(
            username="Renat", email="renat@joutak.ru", password=PW_RENAT
        )
        access, _ = self._jwt_from_session(sess)

        resp = self.c.get(f"{API}/oauth/providers", **auth_header(access))
        self.assertEqual(resp.status_code, 200, resp.content)
        providers = json.loads(resp.content)["providers"]
        self.assertIn("yandex", providers)

        resp = self.c.get(f"{API}/oauth/link/yandex", **auth_header(access))
        self.assertEqual(resp.status_code, 200, resp.content)
        url = json.loads(resp.content)["authorize_url"]
        self.assertTrue(url.startswith("/accounts/yandex/login/"))
"""
