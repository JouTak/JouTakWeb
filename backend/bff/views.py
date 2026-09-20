from __future__ import annotations

import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods
from featureflags.services import (
    build_context,
    clear_override_cookie,
    resolve_optional_user,
    set_override_cookie,
)

from backend.ratelimiting import (
    BFF_ACCOUNT_RATE,
    bff_ratelimit,
)
from bff.services import (
    build_account_summary_payload,
    build_bootstrap_payload,
    build_page_document,
)

_INVALID_FEATURE_OVERRIDE_DETAIL = "Invalid feature override request."


def _invalid_feature_override_response() -> JsonResponse:
    return JsonResponse(
        {"detail": _INVALID_FEATURE_OVERRIDE_DETAIL},
        status=400,
    )


def _build_bff_response(request, *, page, build_payload):
    """
    Construct a BFF JSON response with feature-flag cookies attached.

    The response is created empty first so that ``build_context`` can
    attach Set-Cookie headers (anonymous ID, override cookies). After
    context is ready, the payload is serialized into the response body.
    """
    response = JsonResponse({}, content_type="application/json")
    context, _ = build_context(request, page=page, response=response)
    payload = build_payload(request, context)
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    response.content = JsonResponse(payload).content
    response["Cache-Control"] = "private, no-store"
    response["Vary"] = "Cookie, X-Session-Token, Origin"
    return response


@require_GET
@bff_ratelimit
def bootstrap(request):
    return _build_bff_response(
        request,
        page="bootstrap",
        build_payload=build_bootstrap_payload,
    )


@require_GET
@bff_ratelimit
def itmocraft(request):
    return _build_bff_response(
        request,
        page="itmocraft",
        build_payload=lambda req, context: build_page_document(
            req,
            context,
            product_id="itmocraft",
            requested_path="/",
        ),
    )


@require_GET
@bff_ratelimit
def minigames(request):
    return _build_bff_response(
        request,
        page="minigames",
        build_payload=lambda req, context: build_page_document(
            req,
            context,
            product_id="minigames",
            requested_path="/minigames",
        ),
    )


@require_GET
@bff_ratelimit
def contact(request):
    return _build_bff_response(
        request,
        page="contact",
        build_payload=lambda req, context: build_page_document(
            req,
            context,
            product_id="contact",
            requested_path="/contact",
        ),
    )


@require_GET
@bff_ratelimit
def joutak(request):
    return _build_bff_response(
        request,
        page="joutak",
        build_payload=lambda req, context: build_page_document(
            req,
            context,
            product_id="joutak",
            requested_path="/joutak",
        ),
    )


@require_GET
@bff_ratelimit
def itmocraft_legacy(request):
    return _build_bff_response(
        request,
        page="itmocraft",
        build_payload=lambda req, context: build_page_document(
            req,
            context,
            product_id="itmocraft",
            requested_path="/itmocraft",
            fixed_legacy=True,
        ),
    )


@require_GET
@bff_ratelimit(rate=BFF_ACCOUNT_RATE)
def account_summary(request):
    # Require authentication — unauthenticated users should not
    # receive account data (security hardening).
    user = resolve_optional_user(request)
    if not user or not getattr(user, "is_authenticated", False):
        return JsonResponse(
            {"detail": "Authentication required."},
            status=401,
            content_type="application/json",
        )
    return _build_bff_response(
        request,
        page="account",
        build_payload=build_account_summary_payload,
    )


@require_http_methods(["POST", "DELETE"])
def feature_overrides(request):
    """Manage staff previews through a CSRF-protected unsafe method."""
    user = resolve_optional_user(request)
    if not user or not getattr(user, "is_staff", False):
        return JsonResponse({"detail": "Staff access required."}, status=403)

    response = JsonResponse({"overrides": {}})
    if request.method == "DELETE":
        clear_override_cookie(response)
        return response

    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _invalid_feature_override_response()
    if not isinstance(payload, dict):
        return _invalid_feature_override_response()

    overrides = payload.get("overrides")
    if not isinstance(overrides, dict):
        return _invalid_feature_override_response()

    try:
        validated = set_override_cookie(
            response,
            user=user,
            overrides=overrides,
        )
    except ValueError:
        return _invalid_feature_override_response()
    response.content = JsonResponse({"overrides": validated}).content
    return response
