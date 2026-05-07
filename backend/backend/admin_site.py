from __future__ import annotations

from allauth.mfa.adapter import get_adapter as get_mfa_adapter
from django.conf import settings
from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.html import format_html


def admin_mfa_is_enabled(user: object | None) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return bool(get_mfa_adapter().is_mfa_enabled(user))


class AdminMFAAuthenticationForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user) -> None:
        super().confirm_login_allowed(user)
        if getattr(user, "is_staff", False) and not admin_mfa_is_enabled(user):
            mfa_setup_url = (
                f"{settings.FRONTEND_BASE_URL.rstrip('/')}"
                "/account/security#mfa"
            )
            raise ValidationError(
                format_html(
                    "Admin access requires a configured MFA factor. "
                    '<a href="{}">Open account security settings</a> '
                    "and add an authenticator app code or passkey first.",
                    mfa_setup_url,
                ),
                code="admin_mfa_required",
            )


class JouTakAdminSite(AdminSite):
    site_header = "JouTak Staff Admin"
    site_title = "JouTak Admin"
    index_title = "Operations Console"
    site_url = None
    login_form = AdminMFAAuthenticationForm

    def has_permission(self, request) -> bool:
        user = getattr(request, "user", None)
        return bool(
            user and user.is_active and user.is_authenticated and user.is_staff
        )
