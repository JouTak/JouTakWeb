from django.db import transaction
from ninja import Router, File, Body
from ninja.files import UploadedFile
from ninja.errors import HttpError
from allauth.headless.contrib.ninja.security import x_session_token_auth
from django.contrib.auth import get_user_model
from accounts.transport.schemas import (
    OkOut,
    ChangeEmailIn,
    ProfileUpdateIn,
    EmailStatusOut,
    SessionsOut,
    RevokeSessionsIn,
    ErrorOut,
    RevokeOut,
)
from accounts.services.profile import ProfileService
from accounts.services.emailing import EmailService
from accounts.services.sessions import SessionService

User = get_user_model()
account_router = Router(tags=["Account"], auth=[x_session_token_auth])


def _require_authenticated_user(request) -> User:
    user = getattr(request, "auth", None)
    if not user or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "Not authenticated")
    return user


@account_router.patch(
    "/profile",
    response={200: OkOut, 401: ErrorOut},
    summary="Update profile fields",
    operation_id="account_update_profile",
)
@transaction.atomic
def account_update_profile(request, payload: ProfileUpdateIn = Body(...)):
    user = _require_authenticated_user(request)
    ProfileService.update_name(
        user, first=payload.first_name, last=payload.last_name
    )
    return OkOut(ok=True, message="Профиль обновлён")


@account_router.post(
    "/avatar",
    response={200: OkOut, 401: ErrorOut},
    summary="Upload/replace user avatar",
    operation_id="account_upload_avatar",
)
def upload_avatar(request, avatar: UploadedFile = File(...)):
    user = _require_authenticated_user(request)
    SessionService.assert_session_allowed(request)
    SessionService.touch(request, user)
    updated = ProfileService.save_avatar(user, avatar)
    if updated:
        return OkOut(ok=True, message="Аватар обновлён")
    return OkOut(
        ok=True, message="Поле avatar отсутствует в модели пользователя"
    )


@account_router.get(
    "/email",
    response={200: EmailStatusOut, 401: ErrorOut},
    summary="Get primary email & verification state",
    operation_id="account_email_status",
)
def account_email_status(request):
    user = _require_authenticated_user(request)
    return EmailService.status(user)


@account_router.post(
    "/email/change",
    response={200: OkOut, 400: ErrorOut, 401: ErrorOut},
    summary="Request email change (sends confirmation)",
    operation_id="account_change_email",
)
@transaction.atomic
def account_change_email(request, payload: ChangeEmailIn = Body(...)):
    user = _require_authenticated_user(request)
    EmailService.request_change(request, user, new_email=payload.new_email)
    return OkOut(
        ok=True, message="Проверьте почту, чтобы подтвердить новый адрес"
    )


@account_router.post(
    "/email/resend",
    response={200: OkOut, 401: ErrorOut},
    summary="Resend email confirmation",
    operation_id="account_resend_email",
)
def account_resend_email_verification(request):
    user = _require_authenticated_user(request)
    EmailService.resend_confirmation(request, user)
    return OkOut(ok=True, message="Письмо с подтверждением отправлено")


@account_router.get(
    "/sessions",
    response={200: SessionsOut, 401: ErrorOut},
    summary="List current user sessions",
    operation_id="account_list_sessions",
)
def list_sessions(request):
    user = _require_authenticated_user(request)
    SessionService.assert_session_allowed(request)
    SessionService.touch(request, user)
    return SessionsOut(sessions=SessionService.list(request, user))


@account_router.post(
    "/sessions/bulk",
    response={200: RevokeOut, 401: ErrorOut},
    summary="Revoke sessions in bulk",
    operation_id="account_revoke_sessions_bulk",
)
def revoke_sessions_bulk(request, payload: RevokeSessionsIn):
    _require_authenticated_user(request)
    return SessionService.revoke_bulk(request, payload)


@account_router.post(
    "/sessions/_bulk",
    response={200: RevokeOut, 401: ErrorOut},
    summary="Revoke sessions in bulk (compat)",
    operation_id="account_revoke_sessions_bulk_compat",
)
def revoke_sessions_bulk_compat(request, payload: RevokeSessionsIn):
    _require_authenticated_user(request)
    return SessionService.revoke_bulk(request, payload)


@account_router.delete(
    "/sessions/{sid}",
    response={200: RevokeOut, 401: ErrorOut, 404: ErrorOut},
    summary="Revoke single session",
    operation_id="account_revoke_session",
)
def revoke_session(request, sid: str, reason: str | None = None):
    _require_authenticated_user(request)
    return SessionService.revoke_single(request, sid=sid, reason=reason)
