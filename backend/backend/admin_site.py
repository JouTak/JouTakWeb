from __future__ import annotations

import json
import logging

from accounts.services import admin_mfa as admin_mfa_service
from accounts.services.admin_mfa import (
    SESSION_KEY_ADMIN_MFA_ASSURANCE,
    SESSION_KEY_ADMIN_MFA_PENDING,
    AdminMFAError,
    AdminMFARateLimitError,
    AdminMFAVerificationError,
    abort_pending_admin_login,
    admin_request_has_mfa_assurance,
    admin_user_has_primary_mfa,
    admin_user_has_webauthn,
    begin_admin_webauthn,
    clear_admin_mfa_state,
    complete_admin_login,
    get_pending_admin_login,
    register_failed_webauthn_verification,
    safe_admin_next,
    start_pending_admin_login,
    verify_admin_code,
    verify_admin_webauthn,
)
from django.conf import settings
from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import logout as auth_logout
from django.core.exceptions import ValidationError
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseNotAllowed,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import render
from django.urls import path
from django.utils.html import format_html
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

logger = logging.getLogger(__name__)

# Compatibility aliases for middleware and older tests. The values now hold
# structured, versioned state rather than a user id / boolean.
SESSION_KEY_ADMIN_MFA_VERIFIED = SESSION_KEY_ADMIN_MFA_ASSURANCE
SESSION_KEY_ADMIN_MFA_PENDING_USER = SESSION_KEY_ADMIN_MFA_PENDING
admin_mfa_is_enabled = admin_user_has_primary_mfa
is_admin_mfa_verified = admin_mfa_service.is_admin_mfa_verified


def _audit_event(
    level: int,
    event: str,
    request: HttpRequest,
    *,
    user_id: object | None = None,
    method: str | None = None,
    reason_code: str | None = None,
) -> None:
    extra = {
        "event": event,
        "request_id": getattr(request, "request_id", None),
        "request_host": request.get_host().split(":", 1)[0].lower(),
        "request_path": request.path,
    }
    if user_id is not None:
        extra["user_id"] = str(user_id)
    if method is not None:
        extra["method"] = method
    if reason_code is not None:
        extra["reason_code"] = reason_code
    logger.log(level, event, extra=extra)


def _rate_limited_json(
    request: HttpRequest,
    pending,
) -> JsonResponse:
    abort_pending_admin_login(request, pending)
    response = JsonResponse(
        {"error": "Too many attempts. Start the admin login again."},
        status=429,
    )
    response["Retry-After"] = "60"
    return response


class AdminMFAAuthenticationForm(AdminAuthenticationForm):
    """Admin password form that requires a primary MFA authenticator."""

    def confirm_login_allowed(self, user) -> None:
        super().confirm_login_allowed(user)
        if admin_user_has_primary_mfa(user):
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
        return admin_request_has_mfa_assurance(request)

    def login(self, request: HttpRequest, extra_context=None) -> HttpResponse:
        """Run the password stage without creating an authenticated session."""
        if request.method == "POST":
            # A previous/force-created admin session must not donate either its
            # identity or MFA assurance to a new password flow.
            if getattr(request.user, "is_authenticated", False):
                auth_logout(request)
            else:
                clear_admin_mfa_state(request)

            form = self.login_form(request, data=request.POST)
            if form.is_valid():
                user = form.get_user()
                try:
                    start_pending_admin_login(
                        request,
                        user,
                        next_url=request.POST.get("next"),
                    )
                except AdminMFAVerificationError as exc:
                    # A primary factor can be removed after form validation.
                    # Keep that expected state race fail-closed without
                    # turning it into a 500.
                    form.add_error(
                        None,
                        ValidationError(
                            "Не удалось начать подтверждение. Проверьте "
                            "настройки MFA и попробуйте войти снова.",
                            code="admin_mfa_state_changed",
                        ),
                    )
                    _audit_event(
                        logging.WARNING,
                        "admin.mfa.pending_failed",
                        request,
                        user_id=user.pk,
                        reason_code=exc.reason_code,
                    )
                else:
                    _audit_event(
                        logging.INFO,
                        "admin.mfa.pending_started",
                        request,
                        user_id=user.pk,
                    )
                    return HttpResponseRedirect("/admin/mfa-verify/")

            context = self.each_context(request)
            context.update(
                {
                    "form": form,
                    "title": "Log in",
                    "app_path": request.get_full_path(),
                    "next": safe_admin_next(
                        request,
                        request.POST.get("next"),
                    ),
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

    def mfa_verify_view(self, request: HttpRequest) -> HttpResponse:
        """MFA verification page: TOTP, recovery code, or Passkey."""
        if request.method not in {"GET", "POST"}:
            return HttpResponseNotAllowed(["GET", "POST"])

        pending = get_pending_admin_login(request)
        if not pending:
            _audit_event(
                logging.INFO,
                "admin.mfa.expired",
                request,
                reason_code="pending_missing_or_expired",
            )
            return HttpResponseRedirect("/admin/login/")

        error = ""
        restart_required = False
        status = 200
        if request.method == "POST":
            code = request.POST.get("mfa_code", "").strip()
            try:
                verification = verify_admin_code(
                    request,
                    pending,
                    code,
                )
                next_url = complete_admin_login(
                    request,
                    pending,
                    verification,
                )
            except AdminMFARateLimitError as exc:
                abort_pending_admin_login(request, pending)
                error = "Слишком много попыток. Войдите заново."
                restart_required = True
                status = 429
                _audit_event(
                    logging.WARNING,
                    "admin.mfa.rate_limited",
                    request,
                    user_id=pending.user.pk,
                    method="code",
                    reason_code=exc.reason_code,
                )
            except AdminMFAVerificationError as exc:
                error = (
                    "Введите код подтверждения."
                    if exc.reason_code == "missing_code"
                    else "Неверный код. Попробуйте ещё раз."
                )
                _audit_event(
                    logging.WARNING,
                    "admin.mfa.failed",
                    request,
                    user_id=pending.user.pk,
                    method="code",
                    reason_code=exc.reason_code,
                )
            else:
                _audit_event(
                    logging.INFO,
                    "admin.mfa.succeeded",
                    request,
                    user_id=pending.user.pk,
                    method=verification.method,
                )
                return HttpResponseRedirect(next_url)

        context = {
            "title": "Двухфакторная аутентификация",
            "username": pending.user.get_username(),
            "error": error,
            "has_passkeys": admin_user_has_webauthn(pending.user),
            "restart_required": restart_required,
            "site_header": self.site_header,
            "site_title": self.site_title,
        }
        response = render(
            request,
            "admin/mfa_verify.html",
            context,
            status=status,
        )
        if status == 429:
            response["Retry-After"] = "60"
        return response

    def webauthn_options_view(self, request: HttpRequest) -> HttpResponse:
        """Return admin WebAuthn options with user verification required."""
        if request.method != "GET":
            return HttpResponseNotAllowed(["GET"])

        pending = get_pending_admin_login(request)
        if not pending:
            return JsonResponse({"error": "No pending login"}, status=403)

        try:
            options = begin_admin_webauthn(request, pending)
        except AdminMFARateLimitError as exc:
            _audit_event(
                logging.WARNING,
                "admin.mfa.rate_limited",
                request,
                user_id=pending.user.pk,
                method="webauthn_options",
                reason_code=exc.reason_code,
            )
            return _rate_limited_json(request, pending)
        except AdminMFAError as exc:
            _audit_event(
                logging.WARNING,
                "admin.mfa.failed",
                request,
                user_id=pending.user.pk,
                method="webauthn",
                reason_code=exc.reason_code,
            )
            return JsonResponse(
                {"error": "Unable to start verification"},
                status=400,
            )

        return JsonResponse(options)

    def webauthn_complete_view(self, request: HttpRequest) -> HttpResponse:
        """Verify an admin WebAuthn authentication response."""
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])

        pending = get_pending_admin_login(request)
        if not pending:
            return JsonResponse({"error": "No pending login"}, status=403)

        try:
            credential = json.loads(request.body)
            if not isinstance(credential, dict):
                raise ValueError
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            try:
                register_failed_webauthn_verification(request, pending)
            except AdminMFARateLimitError as exc:
                _audit_event(
                    logging.WARNING,
                    "admin.mfa.rate_limited",
                    request,
                    user_id=pending.user.pk,
                    method="webauthn",
                    reason_code=exc.reason_code,
                )
                return _rate_limited_json(request, pending)
            _audit_event(
                logging.WARNING,
                "admin.mfa.failed",
                request,
                user_id=pending.user.pk,
                method="webauthn",
                reason_code="invalid_json",
            )
            return JsonResponse({"error": "Verification failed"}, status=400)

        try:
            verification = verify_admin_webauthn(
                request,
                pending,
                credential,
            )
            next_url = complete_admin_login(
                request,
                pending,
                verification,
            )
        except AdminMFARateLimitError as exc:
            _audit_event(
                logging.WARNING,
                "admin.mfa.rate_limited",
                request,
                user_id=pending.user.pk,
                method="webauthn",
                reason_code=exc.reason_code,
            )
            return _rate_limited_json(request, pending)
        except AdminMFAVerificationError as exc:
            _audit_event(
                logging.WARNING,
                "admin.mfa.failed",
                request,
                user_id=pending.user.pk,
                method="webauthn",
                reason_code=exc.reason_code,
            )
            return JsonResponse({"error": "Verification failed"}, status=400)
        except Exception:
            # Keep the public response and event payload generic. No credential
            # body, challenge, origin or authenticator material is logged.
            _audit_event(
                logging.ERROR,
                "admin.mfa.failed",
                request,
                user_id=pending.user.pk,
                method="webauthn",
                reason_code="internal_error",
            )
            return JsonResponse({"error": "Verification failed"}, status=400)

        _audit_event(
            logging.INFO,
            "admin.mfa.succeeded",
            request,
            user_id=pending.user.pk,
            method=verification.method,
        )
        return JsonResponse({"ok": True, "redirect": next_url})
