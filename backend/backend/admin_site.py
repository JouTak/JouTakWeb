from __future__ import annotations

import logging

from allauth.mfa.adapter import get_adapter as get_mfa_adapter
from allauth.mfa.models import Authenticator
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
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

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
    Admin login form that blocks staff without MFA enrollment.

    Staff users who have NOT enrolled any MFA factor cannot log in
    and are directed to the frontend security settings page.
    Staff users who HAVE MFA pass form validation — the MFA code
    challenge happens on a separate intermediate page after this.
    """

    def confirm_login_allowed(self, user) -> None:
        super().confirm_login_allowed(user)
        if not getattr(user, "is_staff", False):
            return
        if admin_mfa_is_enabled(user):
            # User has MFA: credentials are valid, MFA step comes next.
            return
        # Staff without MFA: block login entirely.
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
        """
        Strict permission check: staff must be MFA-verified if they
        have MFA enrolled. This prevents any bypass path from granting
        admin access without 2FA completion.
        """
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
        Complete override of admin login. On POST:

        1. Validate credentials via AdminMFAAuthenticationForm
        2. If user has MFA enrolled -> DO NOT call auth_login(), store
           user PK in session, redirect to /admin/mfa-verify/
        3. If user has no MFA -> blocked by confirm_login_allowed()
        4. If form invalid -> show errors, never delegate to super()

        super().login() is ONLY used for GET (render empty form).
        This prevents Django's LoginView.form_valid() from calling
        auth_login() and bypassing the MFA challenge.
        """
        if request.method == "POST":
            form = self.login_form(request, data=request.POST)
            if form.is_valid():
                user = form.get_user()
                if admin_mfa_is_enabled(user):
                    # DO NOT call auth_login(). The user is NOT
                    # authenticated until they pass TOTP/recovery.
                    request.session[SESSION_KEY_ADMIN_MFA_PENDING_USER] = (
                        user.pk
                    )
                    request.session.save()
                    logger.info(
                        "Admin login: credentials valid, MFA required "
                        "for user=%s, redirecting to verify",
                        user.pk,
                    )
                    return HttpResponseRedirect("/admin/mfa-verify/")
                # No MFA enrolled (should not reach here due to
                # confirm_login_allowed, but handle defensively).
                auth_login(request, user)
                request.session[SESSION_KEY_ADMIN_MFA_VERIFIED] = True
                return HttpResponseRedirect(
                    request.POST.get("next", "/admin/")
                )
            # Invalid form: render with errors. Do NOT delegate to
            # super().login() which has its own auth_login() path.
            context = self.each_context(request)
            context.update(
                {
                    "form": form,
                    "title": "Log in",
                    "app_path": request.get_full_path(),
                    **(extra_context or {}),
                }
            )
            return render(request, "admin/login.html", context)

        # GET: delegate to standard admin login view rendering.
        return super().login(request, extra_context=extra_context)

    def get_urls(self):
        custom_urls = [
            path(
                "mfa-verify/",
                never_cache(csrf_protect(self.mfa_verify_view)),
                name="admin_mfa_verify",
            ),
        ]
        return custom_urls + super().get_urls()

    def mfa_verify_view(self, request: HttpRequest) -> HttpResponse:
        """
        MFA verification page: TOTP or recovery code input.

        This view is NOT wrapped in admin_view() (which calls
        has_permission and would create a catch-22 since permission
        requires MFA to be verified). Access is guarded by the
        SESSION_KEY_ADMIN_MFA_PENDING_USER session key.
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
            if not code:
                error = "Please enter a verification code."
            elif self._verify_mfa_code(user, code):
                # MFA verified: NOW we call auth_login() for the first
                # time in this entire flow.
                request.session.pop(SESSION_KEY_ADMIN_MFA_PENDING_USER, None)
                auth_login(request, user)
                request.session[SESSION_KEY_ADMIN_MFA_VERIFIED] = True
                logger.info(
                    "Admin MFA verification successful for user=%s",
                    user.pk,
                )
                return HttpResponseRedirect("/admin/")
            else:
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
        Verify a TOTP or recovery code against the user's allauth.mfa
        enrolled authenticators.

        Uses authenticator.wrap().validate_code() which handles:
        - Secret decryption (via EncryptedMFAAdapter)
        - TOTP time-window tolerance
        - Code reuse prevention
        - Recovery code single-use consumption
        """
        # TOTP authenticators
        totp_authenticators = Authenticator.objects.filter(
            user=user, type=Authenticator.Type.TOTP
        )
        for authenticator in totp_authenticators:
            instance = authenticator.wrap()
            if instance.validate_code(code):
                return True

        # Recovery codes (single-use, consumed on success)
        recovery_authenticators = Authenticator.objects.filter(
            user=user, type=Authenticator.Type.RECOVERY_CODES
        )
        for authenticator in recovery_authenticators:
            instance = authenticator.wrap()
            if instance.validate_code(code):
                return True

        return False
