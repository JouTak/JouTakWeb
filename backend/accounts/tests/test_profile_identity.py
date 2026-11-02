from accounts.services.auth import AuthService
from accounts.services.profile import ProfileService
from accounts.tests.base import APITestCase
from profiles.models import CommunityProfile


class OwnProfileIdentityTests(APITestCase):
    def test_account_identity_reads_current_own_avatar_and_nickname(self):
        user = self.create_legacy_user(username="identity_owner")
        self.assertIsNone(AuthService.profile(user).avatar_url)
        avatar = "/media/hub/" + "a" * 32 + ".webp"
        CommunityProfile.objects.create(
            user=user, avatar_url=avatar, visibility="private"
        )
        ProfileService.update_profile_fields(user, minecraft_nick="NewCraft")
        own = AuthService.profile(user)
        self.assertEqual(own.avatar_url, avatar)
        self.assertEqual(own.minecraft_nick, "NewCraft")
