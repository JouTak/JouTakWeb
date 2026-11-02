from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from ninja.errors import HttpError

from profiles.contact_schemas import ContactsUpdate
from profiles.contacts import save_contacts
from profiles.game_data import GameDataUpdate, read_game_data, save_game_data
from profiles.models import CommunityProfile
from profiles.schemas import ProfileUpdate
from profiles.services import update_profile


@skipUnlessDBFeature("has_select_for_update")
class ProfileConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(
            username="concurrent_editor"
        )
        CommunityProfile.objects.create(user=self.user)

    def concurrent(self, save, first, second):
        barrier = Barrier(2)
        user_id = self.user.pk

        def action(payload):
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=user_id)
                barrier.wait(timeout=5)
                try:
                    save(user, payload)
                    return 200
                except HttpError as exc:
                    return exc.status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(action, [first, second]))
        self.assertEqual(sorted(results), [200, 409])

    def test_profile_snapshot_cannot_win_twice(self):
        self.concurrent(
            update_profile,
            ProfileUpdate(version=1, bio="A"),
            ProfileUpdate(version=1, visibility="public"),
        )
        self.assertEqual(
            CommunityProfile.objects.get(user=self.user).version, 2
        )

    def test_contact_collection_cannot_win_twice(self):
        self.concurrent(
            save_contacts,
            ContactsUpdate(version=1, contacts=[]),
            ContactsUpdate(
                version=1, contacts=[{"type": "vk", "value": "editor"}]
            ),
        )
        self.assertEqual(
            CommunityProfile.objects.get(user=self.user).contacts_version, 2
        )

    def test_game_data_snapshot_cannot_win_twice(self):
        version = read_game_data(self.user).version
        self.concurrent(
            save_game_data,
            GameDataUpdate(version=version, minecraft_nick="FirstCraft"),
            GameDataUpdate(version=version, minecraft_nick="SecondCraft"),
        )
