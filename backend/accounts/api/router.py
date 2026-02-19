from accounts.services.account_status import AccountStatusService
from accounts.services.emailing import EmailService
from accounts.services.profile import ProfileService
from accounts.services.sessions import SessionService
from accounts.transport.schemas import (
    AccountStatusOut,
    ChangeEmailIn,
    DeleteAccountIn,
    EmailStatusOut,
    ErrorOut,
    OkOut,
    ProfileUpdateIn,
    ProfileUpdateOut,
    RevokeOut,
    RevokeSessionsIn,
    SessionsOut,
)
from allauth.headless.contrib.ninja.security import x_session_token_auth
from django.contrib.auth import get_user_model
from django.db import transaction
from ninja import Body, File, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile

User = get_user_model()
account_router = Router(tags=["Account"], auth=[x_session_token_auth])


def _require_authenticated_user(request) -> User:
    user = getattr(request, "auth", None)
    if not user or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "Not authenticated")
    return user


@account_router.patch(
    "/profile",
    response={200: ProfileUpdateOut, 400: ErrorOut, 401: ErrorOut},
    summary="Update profile fields",
    operation_id="account_update_profile",
)
@transaction.atomic
def account_update_profile(request, payload: ProfileUpdateIn = Body(...)):
    user = _require_authenticated_user(request)
    profile = ProfileService.update_profile_fields(
        user,
        first_name=payload.first_name,
        last_name=payload.last_name,
        vk_username=payload.vk_username,
        minecraft_nick=payload.minecraft_nick,
        minecraft_has_license=payload.minecraft_has_license,
        is_itmo_student=payload.is_itmo_student,
        itmo_isu=payload.itmo_isu,
    )
    status = AccountStatusService.get_status(user, profile=profile)
    return ProfileUpdateOut(ok=True, message="Профиль обновлён", **status)


@account_router.get(
    "/status",
    response={200: AccountStatusOut, 401: ErrorOut},
    summary="Get profile personalization status",
    operation_id="account_get_status",
)
def account_status(request):
    user = _require_authenticated_user(request)
    status = AccountStatusService.get_status(user)
    return AccountStatusOut(**status)


@account_router.post(
    "/delete",
    response={200: OkOut, 400: ErrorOut, 401: ErrorOut},
    summary="Delete current account",
    operation_id="account_delete_current",
)
@transaction.atomic
def account_delete(request, payload: DeleteAccountIn = Body(...)):
    user = _require_authenticated_user(request)
    SessionService.assert_session_allowed(request)
    if not user.check_password(payload.current_password):
        raise HttpError(400, "wrong current password")
    user.delete()
    request.session.flush()
    return OkOut(ok=True, message="Аккаунт удалён")


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
    response={200: RevokeOut, 400: ErrorOut, 401: ErrorOut},
    summary="Revoke sessions in bulk",
    operation_id="account_revoke_sessions_bulk",
)
def revoke_sessions_bulk(request, payload: RevokeSessionsIn = Body(...)):
    _require_authenticated_user(request)
    return SessionService.revoke_bulk(request, payload)


@account_router.post(
    "/sessions/_bulk",
    response={200: RevokeOut, 400: ErrorOut, 401: ErrorOut},
    summary="Revoke sessions in bulk (compat)",
    operation_id="account_revoke_sessions_bulk_compat",
)
def revoke_sessions_bulk_compat(
    request, payload: RevokeSessionsIn = Body(...)
):
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
