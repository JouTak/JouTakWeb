from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from featureflags.services import build_context

from bff.services import (
    build_account_summary_payload,
    build_bootstrap_payload,
    build_home_payload,
)


@require_GET
def bootstrap(request):
    response = JsonResponse({})
    context, _created = build_context(
        request, page="homepage", response=response
    )
    response.content = JsonResponse(
        build_bootstrap_payload(request, context)
    ).content
    return response


@require_GET
def homepage(request):
    response = JsonResponse({})
    context, _created = build_context(
        request, page="homepage", response=response
    )
    response.content = JsonResponse(build_home_payload(context)).content
    return response


@require_GET
def account_summary(request):
    response = JsonResponse({})
    context, _created = build_context(
        request, page="account", response=response
    )
    response.content = JsonResponse(
        build_account_summary_payload(request, context)
    ).content
    return response
