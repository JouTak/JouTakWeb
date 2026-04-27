from accounts.services.auth import AuthService
from accounts.services.auth_cookies import (
    delete_refresh_cookie,
    set_refresh_cookie,
)
from accounts.services.sessions import SessionService
from accounts.transport.schemas import (
    ChangePasswordIn,
    ChangePasswordOut,
    ErrorOut,
    OkOut,
    ProfileOut,
    TokenPairOut,
    TokenRefreshIn,
    TokenRefreshOut,
)
from allauth.headless.contrib.ninja.security import x_session_token_auth
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse
from ninja import Body, Router
from ninja.errors import HttpError

auth_router = Router(tags=["Auth"])
BODY_REQUIRED = Body(...)
User = get_user_model()


def _require_active_user(
    request: HttpRequest,
    *,
    touch: bool = False,
) -> User:
    user = getattr(request, "auth", None)
    if not user or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "Not authenticated")
    if not getattr(user, "is_active", False):
        raise HttpError(401, "Not authenticated")
    SessionService.assert_session_allowed(request)
    if touch:
        SessionService.touch(request, user)
    return user


@auth_router.post(
    "/jwt/from_session",
    auth=[x_session_token_auth],
    response={200: TokenPairOut, 401: ErrorOut},
    summary="Issue JWT pair bound to current session",
    operation_id="auth_jwt_from_session",
)
def jwt_from_session(
    request: HttpRequest, response: HttpResponse
) -> TokenPairOut:
    user = _require_active_user(request, touch=True)
    pair = AuthService.issue_pair_for_session(request, user)
    set_refresh_cookie(response, pair.refresh or "")
    return TokenPairOut(access=pair.access)


@auth_router.post(
    "/logout",
    auth=[x_session_token_auth],
    response={200: OkOut, 401: ErrorOut},
    summary="Logout current session",
    operation_id="auth_logout",
)
def logout_current(request: HttpRequest, response: HttpResponse) -> OkOut:
    _require_active_user(request)
    AuthService.logout_current(request)
    delete_refresh_cookie(response)
    return OkOut(ok=True, message="logged out")


@auth_router.get(
    "/me",
    auth=[x_session_token_auth],
    response={200: ProfileOut, 401: ErrorOut},
    summary="Get current user profile",
    operation_id="auth_me",
)
def me(request: HttpRequest) -> ProfileOut:
    user = _require_active_user(request, touch=True)
    return AuthService.profile(user)


@auth_router.post(
    "/change_password",
    auth=[x_session_token_auth],
    response={
        200: ChangePasswordOut,
        400: ErrorOut,
        401: ErrorOut,
        422: ErrorOut,
    },
    summary="Change password (requires current password)",
    operation_id="auth_change_password",
)
def change_password(
    request: HttpRequest,
    payload: ChangePasswordIn = BODY_REQUIRED,
) -> ChangePasswordOut:
    user = _require_active_user(request, touch=True)
    return AuthService.change_password(
        request,
        user,
        payload.current_password,
        payload.new_password,
        logout_current_session=payload.logout_current_session,
    )


@auth_router.post(
    "/refresh",
    response={200: TokenRefreshOut, 401: ErrorOut, 422: ErrorOut},
    summary="Refresh JWT pair",
    operation_id="auth_refresh",
)
def refresh_pair(
    request: HttpRequest,
    response: HttpResponse,
    payload: TokenRefreshIn = BODY_REQUIRED,
) -> TokenRefreshOut:
    pair = AuthService.refresh_pair(request, payload)
    set_refresh_cookie(response, pair.refresh or "")
    return TokenRefreshOut(access=pair.access)
