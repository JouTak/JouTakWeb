from __future__ import annotations

from types import SimpleNamespace

from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from featureflags.services import (
    extract_or_create_anonymous_id,
    read_override_cookie,
    set_override_cookie,
)


class FeaturePreviewCookieTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.staff = SimpleNamespace(
            pk=17,
            is_authenticated=True,
            is_staff=True,
        )

    def test_preview_is_bound_to_staff_user(self):
        response = HttpResponse()
        set_override_cookie(
            response,
            user=self.staff,
            overrides={"site_header_version": "v2"},
        )
        encoded = response.cookies[settings.FEATURE_FLAG_OVERRIDE_COOKIE].value

        request = self.factory.get("/")
        request.COOKIES[settings.FEATURE_FLAG_OVERRIDE_COOKIE] = encoded
        self.assertEqual(
            read_override_cookie(request, user=self.staff),
            {"site_header_version": "v2"},
        )
        other_staff = SimpleNamespace(
            pk=18,
            is_authenticated=True,
            is_staff=True,
        )
        self.assertEqual(
            read_override_cookie(request, user=other_staff),
            {},
        )

    def test_preview_rejects_unknown_or_invalid_values(self):
        with self.assertRaises(ValueError):
            set_override_cookie(
                HttpResponse(),
                user=self.staff,
                overrides={"site_header_version": "true"},
            )
        with self.assertRaises(ValueError):
            set_override_cookie(
                HttpResponse(),
                user=self.staff,
                overrides={"unknown": "v2"},
            )

    def test_unsigned_anonymous_id_is_rotated(self):
        request = self.factory.get("/")
        request.COOKIES[settings.FEATURE_FLAG_ANONYMOUS_ID_COOKIE] = "0" * 32

        anonymous_id, created = extract_or_create_anonymous_id(request)

        self.assertTrue(created)
        self.assertNotEqual(anonymous_id, "0" * 32)
