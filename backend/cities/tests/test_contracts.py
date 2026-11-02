from django.test import SimpleTestCase

from scripts.check_frontend_openapi_contracts import (
    normalize_frontend_path,
    run_contract_checks,
)


class HubContractTests(SimpleTestCase):
    def test_nested_dynamic_paths_are_not_skipped(self):
        self.assertEqual(
            normalize_frontend_path(
                "/cities/${encodeURIComponent(slug)}/members/${membership_id}"
            ),
            "/api/cities/{slug}/members/{membership_id}",
        )

    def test_frontend_calls_and_mutation_bodies_match_openapi(self):
        count, errors = run_contract_checks()
        self.assertGreater(count, 25)
        self.assertEqual(errors, [])
