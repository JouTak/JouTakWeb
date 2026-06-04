from accounts.api.openapi_params import (
    NEXT_OPENAPI_PARAMETER,
    PROVIDER_OPENAPI_PARAMETER,
)
from accounts.api.query_params import optional_str_query
from accounts.services.account_status import AccountStatusService
from accounts.services.oauth import OAuthService
from accounts.services.sessions import SessionService
from accounts.transport.schemas import (
    NEXT_PATH_MAX_LENGTH,
    ErrorOut,
    OAuthLinkOut,
    ProviderIdStr,
    ProvidersOut,
)
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
    return ProvidersOut(providers=OAuthService.list_providers(request))


@router_oauth.get(
    "/link/{provider}",
    response={
        200: OAuthLinkOut,
        400: ErrorOut,
        401: ErrorOut,
        403: ErrorOut,
        404: ErrorOut,
        422: ErrorOut,
    },
    summary="Get authorize URL for linking provider",
    operation_id="oauth_link_provider",
    openapi_extra={
        "parameters": [
            PROVIDER_OPENAPI_PARAMETER,
            NEXT_OPENAPI_PARAMETER,
        ],
    },
)
def link_provider(
    request: HttpRequest,
    provider: ProviderIdStr,
) -> OAuthLinkOut:
    SessionService.assert_session_allowed(request)
    SessionService.touch(request, request.auth)
    AccountStatusService.require_personalized_profile(request.auth)
    next_path = optional_str_query(
        request,
        "next",
        max_length=NEXT_PATH_MAX_LENGTH,
    )
    next_path = OAuthService.sanitize_next_path(next_path)
    data = OAuthService.link_provider(
        request,
        provider,
        next_path=next_path,
    )
    return OAuthLinkOut(**data)
