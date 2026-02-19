from django.test import TestCase


class HealthEndpointTests(TestCase):
    def test_health_returns_alive(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Alive")
