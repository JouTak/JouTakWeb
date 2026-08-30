from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from urllib.parse import urlsplit

from allauth.core import context as allauth_context
from allauth.mfa.adapter import get_adapter as get_mfa_adapter
from allauth.mfa.base.forms import AuthenticateForm as MFAAuthenticateForm
from allauth.mfa.models import Authenticator
from allauth.mfa.webauthn.forms import AuthenticateWebAuthnForm
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
from django.urls import path, reverse
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

SESSION_KEY_ADMIN_MFA_VERIFIED = "_admin_mfa_verified"
SESSION_KEY_ADMIN_MFA_PENDING_USER = "_admin_mfa_pending_user_pk"
SESSION_KEY_ADMIN_MFA_PENDING_ISSUED_AT = "_admin_mfa_pending_issued_at"
SESSION_KEY_ADMIN_MFA_PENDING_AUTH_HASH = "_admin_mfa_pending_auth_hash"
ADMIN_MFA_PENDING_TTL_SECONDS = 5 * 60
ADMIN_PASSKEY_UNAVAILABLE_ERROR = (
    "Passkey authentication is unavailable on this admin host."
)

_ADMIN_MFA_PENDING_SESSION_KEYS = (
    SESSION_KEY_ADMIN_MFA_PENDING_USER,
    SESSION_KEY_ADMIN_MFA_PENDING_ISSUED_AT,
    SESSION_KEY_ADMIN_MFA_PENDING_AUTH_HASH,
)


def admin_mfa_is_enabled(user: object | None) -> bool:
    """Check whether the user has at least one MFA authenticator enrolled."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return bool(get_mfa_adapter().is_mfa_enabled(user))


def is_admin_mfa_verified(request: HttpRequest) -> bool:
    """Check whether the current session completed admin MFA verification."""
    return request.session.get(SESSION_KEY_ADMIN_MFA_VERIFIED, False) is True


def _mfa_setup_url() -> str:
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/account/security#mfa"


def _normalized_hostname(value: str | None) -> str:
    """Normalize a configured/request host without changing RP policy."""
    raw = (value or "").strip()
    if not raw:
        return ""
    parsed = urlsplit(raw if "://" in raw else f"//{raw}")
    return (parsed.hostname or "").rstrip(".").lower()


def admin_webauthn_host_is_compatible(request: HttpRequest) -> bool:
    """Whether the admin host matches an existing API enrollment host.

    This is deliberately conservative. Issue #172 owns the future canonical
    RP/origin policy; this guard only avoids offering a ceremony that the
    browser is guaranteed to reject with today's host-derived allauth RP ID.
    """
    request_host = _normalized_hostname(request.get_host())
    api_hosts = {
        hostname
        for value in settings.DJANGO_API_HOSTS
        if (hostname := _normalized_hostname(value))
    }
    return bool(request_host and request_host in api_hosts)


def _admin_mfa_required_error() -> ValidationError:
    return ValidationError(
        format_html(
            "Для доступа в админку необходим настроенный 2FA. "
            '<a href="{}">Откройте настройки безопасности</a> '
            "и добавьте приложение-аутентификатор или Passkey.",
            _mfa_setup_url(),
        ),
        code="admin_mfa_required",
    )


def _user_has_webauthn(user) -> bool:
    """Check if the user has any WebAuthn authenticators enrolled."""
    return Authenticator.objects.filter(
        user=user, type=Authenticator.Type.WEBAUTHN
    ).exists()


def _user_has_code_mfa(user) -> bool:
    """Check for a TOTP authenticator or recovery-code set."""
    return Authenticator.objects.filter(
        user=user,
        type__in=(
            Authenticator.Type.TOTP,
            Authenticator.Type.RECOVERY_CODES,
        ),
    ).exists()


def _first_form_error(form, field: str, fallback: str) -> str:
    errors = form.errors.get(field)
    return str(errors[0]) if errors else fallback


def _form_has_error_code(form, field: str, code: str) -> bool:
    return any(
        error.code == code for error in form.errors.as_data().get(field, ())
    )


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
        raise _admin_mfa_required_error()


class JouTakAdminSite(AdminSite):
    site_header = "JouTak Staff Admin"
    site_title = "JouTak Admin"
    index_title = "Operations Console"
    site_url = None
    login_form = AdminMFAAuthenticationForm

    def has_permission(self, request) -> bool:
        user = getattr(request, "user", None)
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.is_staff
            and admin_mfa_is_enabled(user)
            and is_admin_mfa_verified(request)
        )

    @method_decorator(sensitive_post_parameters("password"))
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
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
                self._clear_pending_mfa(request)
                request.session.pop(SESSION_KEY_ADMIN_MFA_VERIFIED, None)
                if admin_mfa_is_enabled(user):
                    request.session[SESSION_KEY_ADMIN_MFA_PENDING_USER] = (
                        user.pk
                    )
                    request.session[
                        SESSION_KEY_ADMIN_MFA_PENDING_ISSUED_AT
                    ] = time.time()
                    request.session[
                        SESSION_KEY_ADMIN_MFA_PENDING_AUTH_HASH
                    ] = user.get_session_auth_hash()
                    request.session.save()
                    logger.info(
                        "Admin login: credentials valid, MFA required "
                        "for user=%s, redirecting to verify",
                        user.pk,
                    )
                    return HttpResponseRedirect("/admin/mfa-verify/")
                # Enrollment can change between form validation and this
                # point. Fail closed instead of authenticating without MFA.
                form.add_error(
                    None,
                    _admin_mfa_required_error(),
                )
                logger.warning(
                    "Admin login: MFA enrollment disappeared before "
                    "challenge for user=%s",
                    user.pk,
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
        from featureflags.admin import get_rollout_admin_urls

        custom_urls = [
            path(
                "mfa-verify/",
                never_cache(csrf_protect(self.mfa_verify_view)),
                name="admin_mfa_verify",
            ),
            path(
                "mfa-verify/webauthn-options/",
                never_cache(
                    csrf_protect(require_POST(self.webauthn_options_view))
                ),
                name="admin_mfa_webauthn_options",
            ),
            path(
                "mfa-verify/webauthn-complete/",
                never_cache(
                    csrf_protect(require_POST(self.webauthn_complete_view))
                ),
                name="admin_mfa_webauthn_complete",
            ),
            path(
                "mfa-verify/cancel/",
                never_cache(csrf_protect(require_POST(self.mfa_cancel_view))),
                name="admin_mfa_cancel",
            ),
        ]
        return custom_urls + get_rollout_admin_urls(self) + super().get_urls()

    def get_app_list(self, request, app_label=None):
        from backend.admin_navigation import build_navigation_app_list

        app_list = super().get_app_list(request, app_label)
        rollout_console = None
        can_view_rollouts = request.user.has_perm(
            "featureflags.view_featuredefinition"
        ) and (
            request.user.has_perm("featureflags.view_featurerule")
            or request.user.has_perm("featureflags.change_featurerule")
        )
        if can_view_rollouts:
            can_add_rollout = request.user.has_perms(
                (
                    "featureflags.add_featurerule",
                    "featureflags.view_featuregroup",
                )
            )
            rollout_console = {
                "name": "Управление раскатками",
                "object_name": "GuidedRollout",
                "perms": {
                    "add": can_add_rollout,
                    "change": False,
                    "delete": False,
                    "view": True,
                },
                "admin_url": reverse("admin:featureflags_rollout_index"),
                "add_url": (
                    reverse("admin:featureflags_rollout_add")
                    if can_add_rollout
                    else None
                ),
                "view_only": True,
            }
        return build_navigation_app_list(
            app_list,
            rollout_console=rollout_console,
        )

    @staticmethod
    def _clear_pending_mfa(request: HttpRequest) -> None:
        for key in _ADMIN_MFA_PENDING_SESSION_KEYS:
            request.session.pop(key, None)

    def _get_pending_user(self, request):
        """Resolve and validate the pending MFA user from session."""
        user_model = get_user_model()
        pending_pk = request.session.get(SESSION_KEY_ADMIN_MFA_PENDING_USER)
        pending_issued_at = request.session.get(
            SESSION_KEY_ADMIN_MFA_PENDING_ISSUED_AT
        )
        pending_auth_hash = request.session.get(
            SESSION_KEY_ADMIN_MFA_PENDING_AUTH_HASH
        )
        if (
            not pending_pk
            or pending_issued_at is None
            or not pending_auth_hash
        ):
            self._clear_pending_mfa(request)
            return None

        try:
            pending_age = time.time() - float(pending_issued_at)
        except (TypeError, ValueError):
            self._clear_pending_mfa(request)
            return None
        if pending_age < 0 or pending_age > ADMIN_MFA_PENDING_TTL_SECONDS:
            self._clear_pending_mfa(request)
            return None

        try:
            user = user_model.objects.get(
                pk=pending_pk, is_staff=True, is_active=True
            )
        except user_model.DoesNotExist:
            self._clear_pending_mfa(request)
            return None

        if not constant_time_compare(
            str(pending_auth_hash), user.get_session_auth_hash()
        ) or not admin_mfa_is_enabled(user):
            self._clear_pending_mfa(request)
            return None
        return user

    def _complete_mfa_login(
        self,
        request: HttpRequest,
        user,
        finalize_mfa: Callable[[], None],
    ) -> None:
        """Finalize admin login after MFA verification."""
        self._clear_pending_mfa(request)
        auth_login(
            request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        finalize_mfa()
        request.session[SESSION_KEY_ADMIN_MFA_VERIFIED] = True
        logger.info(
            "Admin MFA verification successful for user=%s",
            user.pk,
        )

    @method_decorator(sensitive_post_parameters("mfa_code"))
    def mfa_verify_view(self, request: HttpRequest) -> HttpResponse:
        """MFA verification page: TOTP, recovery code, or Passkey."""
        user = self._get_pending_user(request)
        if not user:
            return HttpResponseRedirect("/admin/login/")

        has_enrolled_passkeys = _user_has_webauthn(user)
        passkey_host_compatible = admin_webauthn_host_is_compatible(request)
        has_passkeys = has_enrolled_passkeys and passkey_host_compatible
        has_code_factors = _user_has_code_mfa(user)
        passkey_cross_host_blocked = bool(
            has_enrolled_passkeys
            and not passkey_host_compatible
            and not has_code_factors
        )

        error = ""
        if request.method == "POST":
            code = request.POST.get("mfa_code", "").strip()
            if not code:
                error = "Введите код подтверждения."
            else:
                with allauth_context.request_context(request):
                    mfa_form = MFAAuthenticateForm(
                        data={"code": code}, user=user
                    )
                    if mfa_form.is_valid():
                        self._complete_mfa_login(
                            request,
                            user,
                            mfa_form.save,
                        )
                        return HttpResponseRedirect("/admin/")
                    error = _first_form_error(
                        mfa_form,
                        "code",
                        "Неверный код. Попробуйте ещё раз.",
                    )
                    logger.warning(
                        "Admin MFA verification failed for user=%s",
                        user.pk,
                    )

        context = {
            "title": "Двухфакторная аутентификация",
            "username": user.get_username(),
            "error": error,
            "has_passkeys": has_passkeys,
            "has_code_factors": has_code_factors,
            "passkey_cross_host_blocked": passkey_cross_host_blocked,
            "mfa_setup_url": _mfa_setup_url(),
            "site_header": self.site_header,
            "site_title": self.site_title,
        }
        return render(request, "admin/mfa_verify.html", context)

    def mfa_cancel_view(self, request: HttpRequest) -> HttpResponse:
        """Invalidate a pending MFA challenge and return to login."""
        self._clear_pending_mfa(request)
        return HttpResponseRedirect("/admin/login/")

    def webauthn_options_view(self, request: HttpRequest) -> HttpResponse:
        """Return WebAuthn authentication options (challenge) as JSON."""
        from allauth.mfa.webauthn.internal.auth import (
            begin_authentication,
        )

        user = self._get_pending_user(request)
        if not user:
            return JsonResponse({"error": "No pending user"}, status=403)
        if not admin_webauthn_host_is_compatible(request):
            return JsonResponse(
                {"error": ADMIN_PASSKEY_UNAVAILABLE_ERROR},
                status=409,
            )

        # allauth's WebAuthn flow reads the request from a ContextVar.
        # The context manager restores any outer request after this call.
        with allauth_context.request_context(request):
            options = begin_authentication(user=user)

        return JsonResponse(options)

    def webauthn_complete_view(self, request: HttpRequest) -> HttpResponse:
        """Verify a WebAuthn authentication response."""
        user = self._get_pending_user(request)
        if not user:
            return JsonResponse({"error": "No pending user"}, status=403)
        if not admin_webauthn_host_is_compatible(request):
            return JsonResponse(
                {"error": ADMIN_PASSKEY_UNAVAILABLE_ERROR},
                status=409,
            )

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        try:
            with allauth_context.request_context(request):
                mfa_form = AuthenticateWebAuthnForm(
                    data={"credential": body}, user=user
                )
                if mfa_form.is_valid():
                    self._complete_mfa_login(
                        request,
                        user,
                        mfa_form.save,
                    )
                    return JsonResponse({"ok": True, "redirect": "/admin/"})

                rate_limited = _form_has_error_code(
                    mfa_form,
                    "credential",
                    "too_many_login_attempts",
                )
                error = _first_form_error(
                    mfa_form,
                    "credential",
                    "Verification failed",
                )
                logger.warning(
                    "Admin WebAuthn verification failed for user=%s",
                    user.pk,
                )
                return JsonResponse(
                    {"error": error}, status=429 if rate_limited else 400
                )
        except Exception:
            logger.warning(
                "Admin WebAuthn verification failed for user=%s",
                user.pk,
                exc_info=True,
            )
            return JsonResponse({"error": "Verification failed"}, status=400)
