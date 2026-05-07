from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from featureflags.services import build_context

from bff.services import (
    build_account_summary_payload,
    build_bootstrap_payload,
    build_home_payload,
)


def _build_bff_response(request, *, page, build_payload):
    """
    Construct a BFF JSON response with feature-flag cookies attached.

    The response is created empty first so that ``build_context`` can
    attach Set-Cookie headers (anonymous ID, override cookies). After
    context is ready, the payload is serialized into the response body.
    """
    response = JsonResponse({}, content_type="application/json")
    context, _created = build_context(request, page=page, response=response)
    payload = build_payload(request=request, context=context)
    response.content = JsonResponse(payload).content
    return response


@require_GET
def bootstrap(request):
    return _build_bff_response(
        request,
        page="homepage",
        build_payload=lambda request, context: (
            build_bootstrap_payload(request, context)
        ),
    )


@require_GET
def homepage(request):
    return _build_bff_response(
        request,
        page="homepage",
        build_payload=lambda request, context: build_home_payload(context),
    )


@require_GET
def account_summary(request):
    return _build_bff_response(
        request,
        page="account",
        build_payload=lambda request, context: (
            build_account_summary_payload(request, context)
        ),
    )
