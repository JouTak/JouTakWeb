from accounts.tests.base import APITestCase
from cities.tests.test_hub import HubData
from django.contrib.auth import get_user_model


class CityAccountDeletionTests(HubData, APITestCase):
    def test_last_manager_is_protected_even_with_rollout_disabled(self):
        login = self.login(email=self.users["manager"].email)
        self.assertEqual(login.status_code, 200, login.content)
        response = self.post_json(
            "/account/delete",
            {"current_password": self.default_password},
            **self.auth_headers(self.session_token(login)),
        )
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(response.json()["error_code"], "CITY_LAST_MANAGER")
        self.assertTrue(
            get_user_model()
            .objects.filter(pk=self.users["manager"].pk)
            .exists()
        )
