from __future__ import annotations

from django.test import Client, TestCase, override_settings


@override_settings(
    ALLOWED_HOSTS=(
        "localhost",
        "joutak.localhost",
        "api.localhost",
        "admin.localhost",
    ),
    DJANGO_ADMIN_HOSTS=("admin.localhost",),
    DJANGO_API_HOSTS=("joutak.localhost", "api.localhost"),
    CORS_ALLOWED_ORIGINS=("https://joutak.localhost",),
    CORS_ALLOW_CREDENTIALS=True,
    CSRF_TRUSTED_ORIGINS=("http://joutak.localhost",),
    WEBAUTHN_ADMIN_ORIGINS=(
        "http://admin.localhost",
        "http://admin.localhost:8000",
    ),
)
class HostRoutingStaticSecurityTests(TestCase):
    def test_disallowed_host_keeps_request_id_and_security_headers(self):
        response = self.client.get(
            "/admin/",
            HTTP_HOST="evil.example",
        )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.headers["X-Request-ID"])
        self.assertEqual(
            response.headers["X-Content-Type-Options"],
            "nosniff",
        )
        self.assertIn("Referrer-Policy", response.headers)

    def test_admin_static_is_blocked_before_whitenoise_on_api_hosts(self):
        for host in ("joutak.localhost", "api.localhost"):
            with self.subTest(host=host):
                response = self.client.get(
                    "/static/admin/css/base.css",
                    HTTP_HOST=host,
                )
                self.assertEqual(response.status_code, 403)

    def test_admin_static_is_blocked_before_whitenoise_on_unknown_host(self):
        response = self.client.get(
            "/static/admin/css/base.css",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_static_remains_available_on_admin_host(self):
        response = self.client.get(
            "/static/admin/css/base.css",
            HTTP_HOST="admin.localhost",
        )

        # The development test tree has no collected STATIC_ROOT, so
        # WhiteNoise may legitimately return 404 here. The security contract
        # is that HostRoutingMiddleware must not deny the admin host.
        self.assertNotEqual(response.status_code, 403)

    def test_admin_api_and_bff_denials_never_receive_cors_headers(self):
        for method, extra_headers in (
            ("get", {}),
            (
                "options",
                {"HTTP_ACCESS_CONTROL_REQUEST_METHOD": "GET"},
            ),
        ):
            for path in ("/api/auth/status", "/bff/bootstrap"):
                with self.subTest(method=method, path=path):
                    response = getattr(self.client, method)(
                        path,
                        HTTP_HOST="admin.localhost",
                        HTTP_ORIGIN="https://joutak.localhost",
                        **extra_headers,
                    )

                    self.assertEqual(response.status_code, 403)
                    self.assertNotIn(
                        "Access-Control-Allow-Origin",
                        response.headers,
                    )
                    self.assertNotIn(
                        "Access-Control-Allow-Credentials",
                        response.headers,
                    )

    def test_public_api_routes_keep_expected_credentialed_cors_headers(self):
        for host in ("joutak.localhost", "api.localhost"):
            for method, extra_headers in (
                ("get", {}),
                (
                    "options",
                    {"HTTP_ACCESS_CONTROL_REQUEST_METHOD": "GET"},
                ),
            ):
                with self.subTest(host=host, method=method):
                    response = getattr(self.client, method)(
                        "/api/auth/status",
                        HTTP_HOST=host,
                        HTTP_ORIGIN="https://joutak.localhost",
                        **extra_headers,
                    )

                    self.assertEqual(
                        response.headers["Access-Control-Allow-Origin"],
                        "https://joutak.localhost",
                    )
                    self.assertEqual(
                        response.headers["Access-Control-Allow-Credentials"],
                        "true",
                    )

    def _csrf_client_and_token(
        self,
        *,
        host: str = "admin.localhost",
    ) -> tuple[Client, str]:
        client = Client(enforce_csrf_checks=True)
        response = client.get(
            "/admin/login/",
            HTTP_HOST=host,
        )
        self.assertEqual(response.status_code, 200)
        return client, client.cookies["csrftoken"].value

    @staticmethod
    def _admin_login_payload(token: str) -> dict[str, str]:
        return {
            "username": "does-not-exist",
            "password": "invalid-password",
            "csrfmiddlewaretoken": token,
        }

    def test_admin_unsafe_request_accepts_only_exact_admin_origin(self):
        client, token = self._csrf_client_and_token()
        response = client.post(
            "/admin/login/",
            self._admin_login_payload(token),
            HTTP_HOST="admin.localhost",
            HTTP_ORIGIN="http://admin.localhost",
        )

        # Invalid credentials reach the login form, proving both the exact
        # origin guard and Django's CSRF validation accepted the request.
        self.assertEqual(response.status_code, 200)

    def test_admin_unsafe_request_accepts_exact_referer_fallback(self):
        client, token = self._csrf_client_and_token()
        response = client.post(
            "/admin/login/",
            self._admin_login_payload(token),
            HTTP_HOST="admin.localhost",
            HTTP_REFERER="http://admin.localhost/admin/login/?next=/admin/",
        )

        self.assertEqual(response.status_code, 200)

    def test_admin_unsafe_request_rejects_non_exact_browser_context(self):
        rejected_headers = (
            {"HTTP_ORIGIN": "http://joutak.localhost"},
            {"HTTP_ORIGIN": "http://evil.joutak.localhost"},
            {"HTTP_ORIGIN": "null"},
            {"HTTP_ORIGIN": "http://admin.localhost:8000"},
            {"HTTP_ORIGIN": "http://admin.localhost/path"},
            {"HTTP_ORIGIN": "http://admin.localhost?"},
            {"HTTP_ORIGIN": "http://admin.localhost#"},
            {"HTTP_ORIGIN": "http://admin.localhost?#"},
            {"HTTP_ORIGIN": "http://admin.localhost:"},
            {"HTTP_ORIGIN": "not-an-origin"},
            {"HTTP_REFERER": "http://joutak.localhost/admin/"},
            {"HTTP_REFERER": "not-a-referer"},
            {},
        )
        for headers in rejected_headers:
            with self.subTest(headers=headers):
                client, token = self._csrf_client_and_token()
                response = client.post(
                    "/admin/login/",
                    self._admin_login_payload(token),
                    HTTP_HOST="admin.localhost",
                    **headers,
                )

                self.assertEqual(response.status_code, 403)
                self.assertNotIn(
                    "Access-Control-Allow-Origin",
                    response.headers,
                )
                self.assertNotIn(
                    "Access-Control-Allow-Credentials",
                    response.headers,
                )

    def test_admin_origin_rejection_logs_only_safe_structured_context(self):
        secret_origin = "https://evil.example/private-origin-token"

        with self.assertLogs("backend.middleware", level="WARNING") as logs:
            response = self.client.post(
                "/admin/login/",
                HTTP_HOST="admin.localhost",
                HTTP_ORIGIN=secret_origin,
                HTTP_X_REQUEST_ID="origin-rejection-request-id",
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(logs.records), 1)
        record = logs.records[0]
        self.assertEqual(record.event, "admin.origin_rejected")
        self.assertEqual(
            record.reason_code,
            "origin_mismatch_or_invalid",
        )
        self.assertEqual(record.request_id, "origin-rejection-request-id")
        self.assertEqual(record.request_host, "admin.localhost")
        self.assertEqual(record.request_path, "/admin/login/")
        self.assertNotIn(secret_origin, logs.output[0])
        self.assertNotIn(secret_origin, record.getMessage())

    def test_admin_unsafe_request_accepts_configured_exact_dev_port(self):
        client, token = self._csrf_client_and_token(
            host="admin.localhost:8000"
        )
        response = client.post(
            "/admin/login/",
            self._admin_login_payload(token),
            HTTP_HOST="admin.localhost:8000",
            HTTP_ORIGIN="http://admin.localhost:8000",
        )

        self.assertEqual(response.status_code, 200)

    def test_admin_unsafe_request_rejects_matching_unconfigured_port(self):
        client, token = self._csrf_client_and_token(
            host="admin.localhost:8443"
        )
        response = client.post(
            "/admin/login/",
            self._admin_login_payload(token),
            HTTP_HOST="admin.localhost:8443",
            HTTP_ORIGIN="http://admin.localhost:8443",
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_safe_methods_do_not_require_origin_headers(self):
        response = self.client.get(
            "/admin/login/",
            HTTP_HOST="admin.localhost",
            HTTP_ORIGIN="null",
        )

        self.assertEqual(response.status_code, 200)

    @override_settings(
        SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
        WEBAUTHN_ADMIN_ORIGINS=("https://admin.localhost",),
    )
    def test_admin_origin_uses_trusted_forwarded_scheme(self):
        client, token = self._csrf_client_and_token()
        response = client.post(
            "/admin/login/",
            self._admin_login_payload(token),
            HTTP_HOST="admin.localhost",
            HTTP_X_FORWARDED_PROTO="https",
            HTTP_ORIGIN="https://admin.localhost",
        )

        self.assertEqual(response.status_code, 200)
