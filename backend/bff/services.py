from __future__ import annotations

from accounts.services.auth import AuthService
from django.http import HttpRequest
from featureflags.models import FeatureGroup
from featureflags.registry import get_flags_for_page
from featureflags.services import RequestEvaluationContext, evaluate_many

from bff.content import PRODUCT_CONTENT
from bff.schemas import (
    LayoutDecision,
    PageDocument,
    ProductInfo,
    Viewer,
)

PRODUCTS = {
    "itmocraft": {
        "canonical_path": "/",
        "page_flag": "site_itmocraft_page_version",
        "default_project": "itmo_craft",
    },
    "joutak": {
        "canonical_path": "/joutak",
        "page_flag": "site_joutak_page_version",
        "default_project": "jou_tak",
    },
    "minigames": {
        "canonical_path": "/minigames",
        "page_flag": "site_minigames_page_version",
        "default_project": "mini_games",
    },
    "contact": {
        "canonical_path": "/contact",
        "page_flag": "site_contact_page_version",
        "default_project": "jou_tak",
    },
}


def viewer_summary(request: HttpRequest, user: object | None) -> Viewer:
    if not user or not getattr(user, "is_authenticated", False):
        return Viewer(
            is_authenticated=False,
            profile_state="guest",
        )
    profile = AuthService.profile(user)
    return Viewer(
        is_authenticated=True,
        username=profile.username,
        email=profile.email,
        profile_state=profile.profile_state,
        profile_complete=profile.profile_complete,
        personalization_context=profile.personalization_context,
    )


def _is_design_tester(context: RequestEvaluationContext) -> bool:
    if context.user_id is None:
        return False
    return FeatureGroup.objects.filter(
        slug="website-design-testers",
        members__pk=context.user_id,
    ).exists()


def _safe_variant(value: object) -> str:
    return str(value) if value in {"legacy", "v2"} else "legacy"


def build_page_document(
    request: HttpRequest,
    context: RequestEvaluationContext,
    *,
    product_id: str,
    requested_path: str,
    fixed_legacy: bool = False,
) -> PageDocument:
    product = PRODUCTS[product_id]
    decisions = evaluate_many(
        context,
        [
            product["page_flag"],
            "site_header_version",
            "site_footer_version",
        ],
    )
    staff_preview = bool(
        context.is_staff
        and context.request_overrides
        and any(value == "v2" for value in context.request_overrides.values())
    )
    can_see_v2 = _is_design_tester(context) or staff_preview

    page_variant = _safe_variant(decisions[product["page_flag"]])
    if fixed_legacy or not can_see_v2:
        page_variant = "legacy"
    header_variant = _safe_variant(decisions["site_header_version"])
    footer_variant = _safe_variant(decisions["site_footer_version"])
    if not can_see_v2:
        header_variant = "legacy"
        footer_variant = "legacy"

    if fixed_legacy:
        source = "fixed_legacy"
    elif staff_preview and page_variant == "v2":
        source = "staff_preview"
    elif page_variant == "v2":
        source = "feature_flag"
    else:
        source = "default"

    return PageDocument(
        product=ProductInfo(
            id=product_id,
            canonical_path=product["canonical_path"],
            requested_path=requested_path,
            is_legacy_alias=fixed_legacy,
        ),
        effective_page_variant=page_variant,
        variant_source=source,
        layout=LayoutDecision(
            header_variant=header_variant,
            footer_variant=footer_variant,
            default_project=product["default_project"],
        ),
        viewer=viewer_summary(request, context.user),
        content=PRODUCT_CONTENT[product_id][page_variant],
    )


def build_bootstrap_payload(
    request: HttpRequest,
    context: RequestEvaluationContext,
) -> dict[str, object]:
    keys = get_flags_for_page("bootstrap")
    return {
        "viewer": viewer_summary(request, context.user).model_dump(
            mode="json"
        ),
        "features": evaluate_many(context, keys),
        "experiments": {
            "anonymous_id_present": bool(context.anonymous_id),
        },
    }


def build_account_summary_payload(
    request: HttpRequest,
    context: RequestEvaluationContext,
) -> dict[str, object]:
    keys = get_flags_for_page(context.page)
    return {
        "viewer": viewer_summary(request, context.user).model_dump(
            mode="json"
        ),
        "features": evaluate_many(context, keys),
    }
