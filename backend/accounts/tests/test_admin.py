from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from accounts.admin import UserAdmin, _csv_safe_text, export_users_csv
from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from allauth.socialaccount.models import (
    SocialAccount,
    SocialApp,
    SocialToken,
)
from allauth.usersessions.models import UserSession
from axes.models import AccessAttempt, AccessFailureLog, AccessLog
from core.models import UserProfile, UserSessionMeta, UserSessionToken
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken

User = get_user_model()

TECHNICAL_ACCOUNT_MODELS = (
    UserProfile,
    EmailAddress,
    SocialAccount,
    SocialApp,
    SocialToken,
    Authenticator,
    UserSession,
    UserSessionMeta,
    UserSessionToken,
    OutstandingToken,
    BlacklistedToken,
    AccessAttempt,
    AccessLog,
    AccessFailureLog,
)


@override_settings(
    DJANGO_ALLOWED_HOSTS=("admin.localhost",),
    DJANGO_ADMIN_HOSTS=("admin.localhost",),
    DJANGO_API_HOSTS=("api.localhost",),
    WEBAUTHN_ADMIN_ORIGINS=("http://admin.localhost",),
)
class AccountAdminTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(self.superuser)
        session = self.client.session
        session["_admin_mfa_verified"] = True
        session.save()

        self.mfa_patchers = (
            patch(
                "backend.admin_site.admin_mfa_is_enabled",
                return_value=True,
            ),
            patch(
                "backend.admin_site.is_admin_mfa_verified",
                return_value=True,
            ),
            patch(
                "backend.middleware.admin_mfa_is_enabled",
                return_value=True,
            ),
            patch(
                "backend.middleware.is_admin_mfa_verified",
                return_value=True,
            ),
        )
        for patcher in self.mfa_patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def admin_get(self, path: str):
        return self.client.get(path, HTTP_HOST="admin.localhost")

    def test_user_is_the_only_registered_account_aggregate(self):
        self.assertIsInstance(admin.site._registry[User], UserAdmin)
        for model in TECHNICAL_ACCOUNT_MODELS:
            self.assertNotIn(model, admin.site._registry)

        add_response = self.admin_get(reverse("admin:auth_user_add"))
        self.assertEqual(add_response.status_code, 200)
        self.assertContains(add_response, 'name="email"')

    def test_technical_account_admin_direct_urls_are_not_available(self):
        for model in TECHNICAL_ACCOUNT_MODELS:
            path = f"/admin/{model._meta.app_label}/{model._meta.model_name}/"
            with self.subTest(path=path):
                response = self.admin_get(path)
                self.assertEqual(response.status_code, 404)

    def test_user_card_never_renders_raw_auth_or_session_material(self):
        target = User.objects.create_user(
            username="target",
            email="target@example.com",
            password="StrongPass123!",
        )
        EmailAddress.objects.create(
            user=target,
            email=target.email,
            verified=True,
            primary=True,
        )
        social_app = SocialApp.objects.create(
            provider="github",
            name="Sensitive OAuth app",
            client_id="oauth-client-id-secret",
            secret="oauth-client-secret",
            key="oauth-key-secret",
        )
        social_account = SocialAccount.objects.create(
            user=target,
            provider="github",
            uid="provider-uid-secret",
            extra_data={"access_claim": "social-extra-data-secret"},
        )
        SocialToken.objects.create(
            account=social_account,
            app=social_app,
            token="oauth-access-token-secret",
            token_secret="oauth-token-secret-secret",
        )
        Authenticator.objects.create(
            user=target,
            type=Authenticator.Type.TOTP,
            data={"secret": "totp-seed-secret"},
            created_at=datetime(2024, 1, 2, 3, 4, tzinfo=UTC),
            last_used_at=datetime(2025, 2, 3, 4, 5, tzinfo=UTC),
        )
        UserSession.objects.create(
            user=target,
            ip="127.0.0.1",
            user_agent="browser-agent-secret",
            session_key="allauth-session-key-secret",
            data={"payload": "allauth-session-payload-secret"},
        )
        UserSessionMeta.objects.create(
            user=target,
            session_key="session-meta-key-secret",
            session_token="session-meta-token-secret",
            user_agent="session-meta-agent-secret",
        )
        UserSessionToken.objects.create(
            user=target,
            session_key="refresh-session-key-secret",
            refresh_jti="refresh-jti-secret",
        )

        response = self.admin_get(
            reverse("admin:auth_user_change", args=(target.pk,))
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Connected providers:")
        self.assertContains(response, "github")
        self.assertContains(response, "MFA factors:")
        self.assertContains(response, str(Authenticator.Type.TOTP.label))
        self.assertContains(response, "2024")
        self.assertContains(response, "2025")
        self.assertContains(response, "Tracked browser sessions:")
        self.assertContains(response, 'name="extended_profile-0-vk_username"')
        for secret in (
            "oauth-client-id-secret",
            "oauth-client-secret",
            "oauth-key-secret",
            "provider-uid-secret",
            "social-extra-data-secret",
            "oauth-access-token-secret",
            "oauth-token-secret-secret",
            "totp-seed-secret",
            "browser-agent-secret",
            "allauth-session-key-secret",
            "allauth-session-payload-secret",
            "session-meta-key-secret",
            "session-meta-token-secret",
            "session-meta-agent-secret",
            "refresh-session-key-secret",
            "refresh-jti-secret",
        ):
            with self.subTest(secret=secret):
                self.assertNotContains(response, secret)

    def test_non_superuser_cannot_edit_privileges_or_superuser(self):
        operator = User.objects.create_user(
            username="operator",
            email="operator@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        operator.user_permissions.add(
            Permission.objects.get(codename="change_user"),
            Permission.objects.get(codename="delete_user"),
        )
        request = RequestFactory().get("/admin/auth/user/")
        request.user = operator
        model_admin = admin.site._registry[User]

        readonly = model_admin.get_readonly_fields(request, operator)

        self.assertLessEqual(
            {"is_staff", "is_superuser", "groups", "user_permissions"},
            set(readonly),
        )
        self.assertFalse(
            model_admin.has_change_permission(request, self.superuser)
        )
        self.assertFalse(model_admin.has_delete_permission(request, operator))
        self.assertNotIn("export_users_csv", model_admin.get_actions(request))

    def test_crafted_post_cannot_elevate_privileges_or_reset_password(self):
        operator = User.objects.create_user(
            username="account-operator",
            email="account-operator@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        operator.user_permissions.add(
            Permission.objects.get(codename="change_user"),
            Permission.objects.get(codename="view_user"),
        )
        target = User.objects.create_user(
            username="plain-account",
            email="plain-account@example.com",
            password="StrongPass123!",
        )
        privileged_group = Group.objects.create(name="privileged-group")
        dangerous_permission = Permission.objects.get(codename="delete_user")
        self.client.force_login(operator)
        session = self.client.session
        session["_admin_mfa_verified"] = True
        session.save()

        response = self.client.post(
            reverse("admin:auth_user_change", args=(target.pk,)),
            {
                "username": target.username,
                "first_name": "Updated",
                "last_name": "Account",
                "email": target.email,
                "is_active": "on",
                "is_staff": "on",
                "is_superuser": "on",
                "groups": (privileged_group.pk,),
                "user_permissions": (dangerous_permission.pk,),
                "_save": "Save",
            },
            HTTP_HOST="admin.localhost",
            HTTP_ORIGIN="http://admin.localhost",
        )

        self.assertEqual(response.status_code, 302)
        target.refresh_from_db()
        self.assertEqual(target.first_name, "Updated")
        self.assertFalse(target.is_staff)
        self.assertFalse(target.is_superuser)
        self.assertFalse(target.groups.exists())
        self.assertFalse(target.user_permissions.exists())

        password_url = reverse(
            "admin:auth_user_password_change",
            args=(target.pk,),
        )
        self.assertEqual(self.admin_get(password_url).status_code, 403)

        change_page = self.admin_get(
            reverse("admin:auth_user_change", args=(target.pk,))
        )
        self.assertEqual(change_page.status_code, 200)
        self.assertNotContains(change_page, password_url)

        csv_attempt = self.client.post(
            reverse("admin:auth_user_changelist"),
            {
                "action": "export_users_csv",
                "_selected_action": (target.pk,),
                "index": "0",
            },
            HTTP_HOST="admin.localhost",
            HTTP_ORIGIN="http://admin.localhost",
        )
        self.assertEqual(csv_attempt.status_code, 200)
        self.assertFalse(
            csv_attempt.headers["Content-Type"].startswith("text/csv")
        )

    def test_csv_export_is_superuser_only_and_formula_safe(self):
        exported = User.objects.create_user(
            username="+spreadsheet-command",
            email=" =spreadsheet-command@example.com",
            password="StrongPass123!",
        )
        request = RequestFactory().post("/admin/auth/user/")
        request.user = self.superuser

        response = export_users_csv(
            admin.site._registry[User],
            request,
            User.objects.filter(pk=exported.pk),
        )

        body = response.content.decode("utf-8")
        self.assertIn("'+spreadsheet-command", body)
        self.assertIn("'=spreadsheet-command@example.com", body)
        self.assertNotIn("vk_username", body)
        self.assertNotIn("itmo_isu", body)
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

        request.user = User.objects.create_user(
            username="not-superuser",
            password="StrongPass123!",
            is_staff=True,
        )
        with self.assertRaises(PermissionDenied):
            export_users_csv(
                admin.site._registry[User],
                request,
                User.objects.filter(pk=exported.pk),
            )

    def test_csv_formula_guard_handles_control_and_whitespace_prefixes(self):
        for value in (
            "=formula",
            "+formula",
            "-formula",
            "@formula",
            "\tformula",
            "\rformula",
            "\nformula",
            "  =formula",
        ):
            with self.subTest(value=value):
                self.assertTrue(_csv_safe_text(value).startswith("'"))

        self.assertEqual(_csv_safe_text("normal value"), "normal value")
