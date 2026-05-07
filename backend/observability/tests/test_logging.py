from __future__ import annotations

from unittest.mock import Mock, patch

from django.http import HttpResponse
from django.test import SimpleTestCase

from backend.middleware import (
    RequestContextMiddleware,
    is_admin_host,
    is_api_host,
)
from observability.logging import (
    RequestLogContextFilter,
    clear_request_log_context,
    set_request_log_context,
)


class ObservabilityHelpersTests(SimpleTestCase):
    def test_request_context_filter_enriches_log_record(self):
        tokens = set_request_log_context(
            request_id="req-123",
            request_host="admin.localhost",
            request_path="/admin/",
        )
        try:
            record = Mock()
            allowed = RequestLogContextFilter().filter(record)
        finally:
            clear_request_log_context(tokens)

        self.assertTrue(allowed)
        self.assertEqual(record.request_id, "req-123")
        self.assertEqual(record.request_host, "admin.localhost")
        self.assertEqual(record.request_path, "/admin/")
        self.assertTrue(record.trace_id)
        self.assertTrue(record.span_id)

    def test_request_context_middleware_sets_response_header(self):
        request = self.client.request().wsgi_request
        request.META["HTTP_HOST"] = "localhost"
        request.path = "/health/"
        middleware = RequestContextMiddleware(
            lambda req: HttpResponse("ok", content_type="text/plain")
        )

        response = middleware(request)

        self.assertIn("X-Request-ID", response)

    @patch("backend.middleware.settings")
    def test_host_helpers_match_configured_hosts(self, mocked_settings):
        mocked_settings.DJANGO_ADMIN_HOSTS = ("admin.localhost",)
        mocked_settings.DJANGO_API_HOSTS = ("api.localhost",)

        self.assertTrue(is_admin_host("admin.localhost"))
        self.assertFalse(is_admin_host("api.localhost"))
        self.assertTrue(is_api_host("api.localhost:80"))
        self.assertFalse(is_api_host("localhost"))
