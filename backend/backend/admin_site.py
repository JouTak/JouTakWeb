from __future__ import annotations

import json
import logging

from allauth.mfa.adapter import get_adapter as get_mfa_adapter
from allauth.mfa.models import Authenticator
from django.conf import settings
from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.core.exceptions import ValidationError
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
)
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


def _user_has_webauthn(user) -> bool:
    """Check if the user has any WebAuthn authenticators enrolled."""
    return Authenticator.objects.filter(
        user=user, type=Authenticator.Type.WEBAUTHN
    ).exists()


class AdminMFAAuthenticationForm(AdminAuthenticationForm):
    """
    Admin login form that blocks staff without MFA enrollment.
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
                "Для доступа в админку необходим настроенный 2FA. "
                '<a href="{}">Откройте настройки безопасности</a> '
                "и добавьте приложение-аутентификатор или Passkey.",
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
        Complete override of admin login POST. Never delegates to
        super().login() on POST to prevent LoginView.form_valid()
        from calling auth_login() and bypassing MFA.
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
                    logger.info(
                        "Admin login: credentials valid, MFA required "
                        "for user=%s, redirecting to verify",
                        user.pk,
                    )
                    return HttpResponseRedirect("/admin/mfa-verify/")
                auth_login(
                    request,
                    user,
                    backend=("django.contrib.auth.backends.ModelBackend"),
                )
                request.session[SESSION_KEY_ADMIN_MFA_VERIFIED] = True
                return HttpResponseRedirect(
                    request.POST.get("next", "/admin/")
                )
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

        return super().login(request, extra_context=extra_context)

    def get_urls(self):
        custom_urls = [
            path(
                "mfa-verify/",
                never_cache(csrf_protect(self.mfa_verify_view)),
                name="admin_mfa_verify",
            ),
            path(
                "mfa-verify/webauthn-options/",
                never_cache(csrf_protect(self.webauthn_options_view)),
                name="admin_mfa_webauthn_options",
            ),
            path(
                "mfa-verify/webauthn-complete/",
                never_cache(csrf_protect(self.webauthn_complete_view)),
                name="admin_mfa_webauthn_complete",
            ),
        ]
        return custom_urls + super().get_urls()

    def _get_pending_user(self, request):
        """Resolve and validate the pending MFA user from session."""
        user_model = get_user_model()
        pending_pk = request.session.get(SESSION_KEY_ADMIN_MFA_PENDING_USER)
        if not pending_pk:
            return None
        try:
            return user_model.objects.get(
                pk=pending_pk, is_staff=True, is_active=True
            )
        except user_model.DoesNotExist:
            request.session.pop(SESSION_KEY_ADMIN_MFA_PENDING_USER, None)
            return None

    def _complete_mfa_login(self, request, user):
        """Finalize admin login after MFA verification."""
        request.session.pop(SESSION_KEY_ADMIN_MFA_PENDING_USER, None)
        auth_login(
            request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        request.session[SESSION_KEY_ADMIN_MFA_VERIFIED] = True
        logger.info(
            "Admin MFA verification successful for user=%s",
            user.pk,
        )

    def mfa_verify_view(self, request: HttpRequest) -> HttpResponse:
        """MFA verification page: TOTP, recovery code, or Passkey."""
        user = self._get_pending_user(request)
        if not user:
            return HttpResponseRedirect("/admin/login/")

        has_passkeys = _user_has_webauthn(user)

        error = ""
        if request.method == "POST":
            code = request.POST.get("mfa_code", "").strip()
            if not code:
                error = "Введите код подтверждения."
            elif self._verify_mfa_code(user, code):
                self._complete_mfa_login(request, user)
                return HttpResponseRedirect("/admin/")
            else:
                error = "Неверный код. Попробуйте ещё раз."
                logger.warning(
                    "Admin MFA verification failed for user=%s",
                    user.pk,
                )

        context = {
            "title": "Двухфакторная аутентификация",
            "username": user.get_username(),
            "error": error,
            "has_passkeys": has_passkeys,
            "site_header": self.site_header,
            "site_title": self.site_title,
        }
        return render(request, "admin/mfa_verify.html", context)

    def webauthn_options_view(self, request: HttpRequest) -> HttpResponse:
        """Return WebAuthn authentication options (challenge) as JSON."""
        from allauth.core import context as allauth_context
        from allauth.mfa.webauthn.internal.auth import (
            begin_authentication,
        )

        user = self._get_pending_user(request)
        if not user:
            return JsonResponse({"error": "No pending user"}, status=403)

        # allauth's webauthn uses context.request for session state
        allauth_context.request = request
        try:
            options = begin_authentication(user=user)
        finally:
            allauth_context.request = None

        return JsonResponse(options)

    def webauthn_complete_view(self, request: HttpRequest) -> HttpResponse:
        """Verify a WebAuthn authentication response."""
        from allauth.core import context as allauth_context
        from allauth.mfa.webauthn.internal.auth import (
            complete_authentication,
        )

        user = self._get_pending_user(request)
        if not user:
            return JsonResponse({"error": "No pending user"}, status=403)

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        allauth_context.request = request
        try:
            complete_authentication(user, body)
        except Exception:
            logger.warning(
                "Admin WebAuthn verification failed for user=%s",
                user.pk,
            )
            return JsonResponse({"error": "Verification failed"}, status=400)
        finally:
            allauth_context.request = None

        self._complete_mfa_login(request, user)
        return JsonResponse({"ok": True, "redirect": "/admin/"})

    @staticmethod
    def _verify_mfa_code(user, code: str) -> bool:
        """
        Verify a TOTP or recovery code against allauth.mfa
        enrolled authenticators.
        """
        totp_authenticators = Authenticator.objects.filter(
            user=user, type=Authenticator.Type.TOTP
        )
        for authenticator in totp_authenticators:
            instance = authenticator.wrap()
            if instance.validate_code(code):
                return True

        recovery_authenticators = Authenticator.objects.filter(
            user=user, type=Authenticator.Type.RECOVERY_CODES
        )
        for authenticator in recovery_authenticators:
            instance = authenticator.wrap()
            if instance.validate_code(code):
                return True

        return False
