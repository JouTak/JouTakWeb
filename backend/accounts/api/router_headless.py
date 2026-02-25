from accounts.services.headless import HeadlessService
from accounts.transport.schemas import ErrorOut, LoginIn, LoginOut, SignupIn
from django.http import HttpRequest
from ninja import Body, Router
from ninja.responses import Response

headless_router = Router(tags=["Auth"])
BODY_REQUIRED = Body(...)


@headless_router.post(
    "/login",
    response={200: LoginOut, 400: ErrorOut},
    summary="Headless login, issues X-Session-Token",
    operation_id="headless_login",
)
def login(
    request: HttpRequest,
    payload: LoginIn = BODY_REQUIRED,
) -> Response:
    st = HeadlessService.login(request, payload.username, payload.password)
    body = {"meta": {"session_token": st}}
    return Response(
        body, headers={"X-Session-Token": st, "Cache-Control": "no-store"}
    )


@headless_router.post(
    "/signup",
    response={200: LoginOut, 400: ErrorOut},
    summary="Headless signup + login, issues X-Session-Token",
    operation_id="headless_signup",
)
def signup(
    request: HttpRequest,
    payload: SignupIn = BODY_REQUIRED,
) -> Response:
    st = HeadlessService.signup(
        request, payload.username, payload.email, payload.password
    )
    return Response(
        {"meta": {"session_token": st}},
        headers={"X-Session-Token": st, "Cache-Control": "no-store"},
    )
