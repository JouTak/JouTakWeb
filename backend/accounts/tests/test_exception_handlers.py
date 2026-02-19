from __future__ import annotations

from accounts.api.exception_handlers import (
    _normalize_error_payload,
    _normalize_form_errors,
)
from django.test import TestCase


class ExceptionHandlerHelperTests(TestCase):
    def test_normalize_form_errors_returns_structured_maps(self):
        raw = (
            '{"field":[{"message":"Ошибка","code":"invalid"}],'
            '"name":["Обязательное поле"]}'
        )
        errors, fields = _normalize_form_errors(raw)

        self.assertIn("field", errors)
        self.assertEqual(errors["field"][0]["message"], "Ошибка")
        self.assertEqual(errors["field"][0]["code"], "invalid")
        self.assertEqual(fields["name"], "Обязательное поле")

    def test_normalize_form_errors_handles_non_json(self):
        errors, fields = _normalize_form_errors("not-json")
        self.assertIsNone(errors)
        self.assertIsNone(fields)

    def test_normalize_error_payload_with_business_code(self):
        payload = _normalize_error_payload(
            '{"detail":"Forbidden","error_code":"E_CODE",'
            '"blocking_reasons":["REASON_1"]}'
        )
        self.assertEqual(payload["detail"], "Forbidden")
        self.assertEqual(payload["error_code"], "E_CODE")
        self.assertEqual(payload["blocking_reasons"], ["REASON_1"])

    def test_normalize_error_payload_returns_none_for_unknown_shape(self):
        payload = _normalize_error_payload('{"message":"plain"}')
        self.assertIsNone(payload)
