from __future__ import annotations

from accounts.services.auth import AuthService
from django.http import HttpRequest
from featureflags.registry import (
    PERSONALIZATION_FLAG_KEYS,
    get_flags_for_page,
)
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
}


def viewer_summary(
    request: HttpRequest,
    user: object | None,
    *,
    feature_decisions: dict[str, bool | str] | None = None,
) -> Viewer:
    if not user or not getattr(user, "is_authenticated", False):
        return Viewer(
            is_authenticated=False,
            profile_state="guest",
        )
    profile = AuthService.profile(
        user,
        feature_decisions=feature_decisions,
    )
    return Viewer(
        is_authenticated=True,
        username=profile.username,
        email=profile.email,
        profile_state=profile.profile_state,
        profile_complete=profile.profile_complete,
        personalization_context=profile.personalization_context,
    )


def _safe_variant(value: object) -> str:
    return str(value) if value in {"legacy", "v2"} else "legacy"


def _evaluate_with_viewer_features(
    context: RequestEvaluationContext,
    keys: list[str] | tuple[str, ...],
) -> dict[str, bool | str]:
    """Evaluate payload and viewer flags in one consistent DB snapshot."""
    viewer_keys = PERSONALIZATION_FLAG_KEYS if context.user_id else ()
    all_keys = list(dict.fromkeys((*keys, *viewer_keys)))
    return evaluate_many(context, all_keys)


def build_page_document(
    request: HttpRequest,
    context: RequestEvaluationContext,
    *,
    product_id: str,
    requested_path: str,
    fixed_legacy: bool = False,
) -> PageDocument:
    product = PRODUCTS[product_id]
    decisions = _evaluate_with_viewer_features(
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
        and context.request_overrides.get(product["page_flag"]) == "v2"
    )

    page_variant = _safe_variant(decisions[product["page_flag"]])
    if fixed_legacy:
        page_variant = "legacy"
    header_variant = _safe_variant(decisions["site_header_version"])
    footer_variant = _safe_variant(decisions["site_footer_version"])

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
        viewer=viewer_summary(
            request,
            context.user,
            feature_decisions=decisions,
        ),
        content=PRODUCT_CONTENT[product_id][page_variant],
    )


def build_bootstrap_payload(
    request: HttpRequest,
    context: RequestEvaluationContext,
) -> dict[str, object]:
    keys = get_flags_for_page("bootstrap")
    decisions = _evaluate_with_viewer_features(context, keys)
    return {
        "viewer": viewer_summary(
            request,
            context.user,
            feature_decisions=decisions,
        ).model_dump(mode="json"),
        "features": {key: decisions[key] for key in keys},
        "experiments": {
            "anonymous_id_present": bool(context.anonymous_id),
        },
    }


def build_account_summary_payload(
    request: HttpRequest,
    context: RequestEvaluationContext,
) -> dict[str, object]:
    keys = get_flags_for_page(context.page)
    decisions = _evaluate_with_viewer_features(context, keys)
    return {
        "viewer": viewer_summary(
            request,
            context.user,
            feature_decisions=decisions,
        ).model_dump(mode="json"),
        "features": {key: decisions[key] for key in keys},
    }
