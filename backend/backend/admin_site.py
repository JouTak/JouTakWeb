from __future__ import annotations

import logging

from allauth.mfa.adapter import get_adapter as get_mfa_adapter
from allauth.mfa.models import Authenticator
from allauth.mfa.totp import validate_totp_code
from django.conf import settings
from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path
from django.utils.html import format_html

logger = logging.getLogger(__name__)

SESSION_KEY_ADMIN_MFA_VERIFIED = "_admin_mfa_verified"
SESSION_KEY_ADMIN_MFA_PENDING_USER = "_admin_mfa_pending_user_pk"


def admin_mfa_is_enabled(user: object | None) -> bool:
    """Check whether the user has at least one MFA authenticator enrolled."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return bool(get_mfa_adapter().is_mfa_enabled(user))


def is_admin_mfa_verified(request: HttpRequest) -> bool:
    """Check whether the current session completed admin MFA verification."""
    return request.session.get(SESSION_KEY_ADMIN_MFA_VERIFIED, False) is True


class AdminMFAAuthenticationForm(AdminAuthenticationForm):
    """
    Standard admin login form with an additional enrollment gate.

    Blocks login for staff users who have NOT enrolled any MFA factor,
    directing them to the frontend security settings page.
    """

    def confirm_login_allowed(self, user) -> None:
        super().confirm_login_allowed(user)
        if not getattr(user, "is_staff", False):
            return
        if admin_mfa_is_enabled(user):
            return
        mfa_setup_url = (
            f"{settings.FRONTEND_BASE_URL.rstrip('/')}/account/security#mfa"
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
        if not (
            user and user.is_active and user.is_authenticated and user.is_staff
        ):
            return False
        if admin_mfa_is_enabled(user):
            return is_admin_mfa_verified(request)
        return True

    def login(self, request: HttpRequest, extra_context=None) -> HttpResponse:
        """
        Override login to inject a TOTP/recovery-code challenge after
        successful password authentication for users with MFA enrolled.
        """
        if request.method == "POST":
            form = self.login_form(request, data=request.POST)
            if form.is_valid():
                user = form.get_user()
                if admin_mfa_is_enabled(user):
                    request.session[SESSION_KEY_ADMIN_MFA_PENDING_USER] = (
                        user.pk
                    )
                    request.session.save()
                    return HttpResponseRedirect("/admin/mfa-verify/")
                auth_login(request, user)
                request.session[SESSION_KEY_ADMIN_MFA_VERIFIED] = True
                return HttpResponseRedirect(
                    request.POST.get("next", "/admin/")
                )

        return super().login(request, extra_context=extra_context)

    def get_urls(self):
        custom_urls = [
            path(
                "mfa-verify/",
                self.admin_view(self.mfa_verify_view, cacheable=False),
                name="admin_mfa_verify",
            ),
        ]
        return custom_urls + super().get_urls()

    def mfa_verify_view(self, request: HttpRequest) -> HttpResponse:
        """
        Intermediate MFA verification page.
        Accepts TOTP or recovery codes.
        """
        user_model = get_user_model()
        pending_pk = request.session.get(SESSION_KEY_ADMIN_MFA_PENDING_USER)

        if not pending_pk:
            return HttpResponseRedirect("/admin/login/")

        try:
            user = user_model.objects.get(
                pk=pending_pk, is_staff=True, is_active=True
            )
        except user_model.DoesNotExist:
            request.session.pop(SESSION_KEY_ADMIN_MFA_PENDING_USER, None)
            return HttpResponseRedirect("/admin/login/")

        error = ""
        if request.method == "POST":
            code = request.POST.get("mfa_code", "").strip()
            if code and self._verify_mfa_code(user, code):
                request.session.pop(SESSION_KEY_ADMIN_MFA_PENDING_USER, None)
                auth_login(request, user)
                request.session[SESSION_KEY_ADMIN_MFA_VERIFIED] = True
                logger.info(
                    "Admin MFA verification successful for user=%s",
                    user.pk,
                )
                return HttpResponseRedirect("/admin/")
            error = "Invalid code. Please try again."
            logger.warning(
                "Admin MFA verification failed for user=%s",
                user.pk,
            )

        context = {
            "title": "Two-Factor Authentication",
            "username": user.get_username(),
            "error": error,
            "site_header": self.site_header,
            "site_title": self.site_title,
        }
        return render(request, "admin/mfa_verify.html", context)

    @staticmethod
    def _verify_mfa_code(user, code: str) -> bool:
        """
        Verify a TOTP or recovery code against the user's enrolled
        authenticators via allauth.mfa infrastructure.
        """
        totp_authenticators = Authenticator.objects.filter(
            user=user, type=Authenticator.Type.TOTP
        )
        for _authenticator in totp_authenticators:
            try:
                if validate_totp_code(user, code):
                    return True
            except Exception:
                continue

        recovery_authenticators = Authenticator.objects.filter(
            user=user, type=Authenticator.Type.RECOVERY_CODES
        )
        for authenticator in recovery_authenticators:
            instance = authenticator.wrap()
            if instance.validate_code(code):
                return True

        return False
