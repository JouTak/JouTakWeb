from ninja import Router, Body
from allauth.headless.contrib.ninja.security import x_session_token_auth
from accounts.transport.schemas import (
    ErrorOut,
    OkOut,
    TokenPairOut,
    TokenRefreshIn,
    TokenRefreshOut,
    ChangePasswordIn,
    ProfileOut,
)
from accounts.services.auth import AuthService

auth_router = Router(tags=["Auth"])


@auth_router.post(
    "/jwt/from_session",
    auth=[x_session_token_auth],
    response={200: TokenPairOut, 401: ErrorOut},
    summary="Issue JWT pair bound to current session",
    operation_id="auth_jwt_from_session",
)
def jwt_from_session(request):
    return AuthService.issue_pair_for_session(request, request.auth)


@auth_router.post(
    "/logout",
    auth=[x_session_token_auth],
    response={200: OkOut},
    summary="Logout current session",
    operation_id="auth_logout",
)
def logout_current(request):
    AuthService.logout_current(request)
    return OkOut(ok=True, message="logged out")


@auth_router.get(
    "/me",
    auth=[x_session_token_auth],
    response={200: ProfileOut, 401: ErrorOut},
    summary="Get current user profile",
    operation_id="auth_me",
)
def me(request):
    return AuthService.profile(request.auth)


@auth_router.post(
    "/change_password",
    auth=[x_session_token_auth],
    response={200: OkOut, 400: ErrorOut, 401: ErrorOut},
    summary="Change password (requires current password)",
    operation_id="auth_change_password",
)
def change_password(request, payload: ChangePasswordIn = Body(...)):
    AuthService.change_password(
        request.auth, payload.current_password, payload.new_password
    )
    return OkOut(ok=True, message="password changed")


@auth_router.post(
    "/refresh",
    response={200: TokenRefreshOut, 401: ErrorOut},
    summary="Refresh JWT pair",
    operation_id="auth_refresh",
)
def refresh_pair(request, payload: TokenRefreshIn = Body(...)):
    return AuthService.refresh_pair(payload)
