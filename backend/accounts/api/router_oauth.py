from accounts.services.account_status import AccountStatusService
from accounts.services.oauth import OAuthService
from accounts.services.sessions import SessionService
from accounts.transport.schemas import ErrorOut, OAuthLinkOut, ProvidersOut
from allauth.headless.contrib.ninja.security import x_session_token_auth
from django.http import HttpRequest
from ninja import Router

router_oauth = Router(tags=["OAuth"], auth=[x_session_token_auth])


@router_oauth.get(
    "/providers",
    response={200: ProvidersOut, 401: ErrorOut},
    summary="List configured OAuth providers",
    operation_id="oauth_list_providers",
)
def list_providers(request: HttpRequest) -> ProvidersOut:
    SessionService.assert_session_allowed(request)
    SessionService.touch(request, request.auth)
    return ProvidersOut(providers=OAuthService.list_providers())


@router_oauth.get(
    "/link/{provider}",
    response={200: OAuthLinkOut, 401: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    summary="Get authorize URL for linking provider",
    operation_id="oauth_link_provider",
)
def link_provider(
    request: HttpRequest,
    provider: str,
) -> OAuthLinkOut:
    SessionService.assert_session_allowed(request)
    SessionService.touch(request, request.auth)
    AccountStatusService.require_personalized_profile(request.auth)
    next_path = OAuthService.sanitize_next_path(request.GET.get("next"))
    data = OAuthService.link_provider(provider, next_path=next_path)
    return OAuthLinkOut(**data)
