from ninja import Router, Body
from ninja.responses import Response
from accounts.transport.schemas import ErrorOut, LoginOut, LoginIn, SignupIn
from accounts.services.headless import HeadlessService

headless_router = Router(tags=["Auth"])


@headless_router.post(
    "/login",
    response={200: LoginOut, 400: ErrorOut},
    summary="Headless login, issues X-Session-Token",
    operation_id="headless_login",
)
def login(request, payload: LoginIn = Body(...)):
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
def signup(request, payload: SignupIn = Body(...)):
    st = HeadlessService.signup(
        request, payload.username, payload.email, payload.password
    )
    return Response(
        {"meta": {"session_token": st}},
        headers={"X-Session-Token": st, "Cache-Control": "no-store"},
    )
