from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InternalAction(ContractModel):
    kind: Literal["internal"]
    path: str


class ExternalAction(ContractModel):
    kind: Literal["external"]
    href: HttpUrl


class DesignPlaceholderAction(ContractModel):
    kind: Literal["design_placeholder"]
    id: str
    behavior: Literal["no_op", "hash"]


ActionRef = Annotated[
    InternalAction | ExternalAction | DesignPlaceholderAction,
    Field(discriminator="kind"),
]


class AssetMedia(ContractModel):
    kind: Literal["asset"]
    id: str
    alt: str


class RemoteMedia(ContractModel):
    kind: Literal["remote"]
    url: HttpUrl
    alt: str


class DesignPlaceholderMedia(ContractModel):
    kind: Literal["design_placeholder"]
    id: str
    alt: str
    broken: bool = False


MediaRef = Annotated[
    AssetMedia | RemoteMedia | DesignPlaceholderMedia,
    Field(discriminator="kind"),
]


class HeroSection(ContractModel):
    type: Literal["hero"]
    background: MediaRef
    logo: MediaRef
    eyebrow: str | None = None
    title: str
    description: str | None = None
    primary_action: ActionRef | None = None


class ProjectItem(ContractModel):
    id: str
    title: str
    description: str
    image: MediaRef
    action: ActionRef


class ProjectsSection(ContractModel):
    type: Literal["projects"]
    title: str
    items: list[ProjectItem]


class EventItem(ContractModel):
    id: str
    title: str
    description: str
    location: str
    image: MediaRef
    starts_at: datetime
    action: ActionRef
    action_label: str = "Регистрация"

    @field_validator("starts_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("starts_at must include a timezone")
        return value


class EventsSection(ContractModel):
    type: Literal["events"]
    title: str
    items: list[EventItem]


class ProductFact(ContractModel):
    id: str
    label: str
    value: str


class ProductActionItem(ContractModel):
    id: str
    label: str
    action: ActionRef
    emphasis: Literal["primary", "secondary", "tertiary"] = "secondary"


class ProductActionsSection(ContractModel):
    type: Literal["actions"]
    eyebrow: str | None = None
    title: str
    description: str
    facts: list[ProductFact] = Field(default_factory=list)
    items: list[ProductActionItem]


class GalleryItem(ContractModel):
    id: str
    label: str
    cover: MediaRef
    photos: list[MediaRef]


class GallerySection(ContractModel):
    type: Literal["gallery"]
    title: str
    items: list[GalleryItem]


class FAQItem(ContractModel):
    id: str
    question: str
    answer: str


class FAQSection(ContractModel):
    type: Literal["faq"]
    title: str
    items: list[FAQItem]


Section = Annotated[
    HeroSection
    | ProjectsSection
    | EventsSection
    | ProductActionsSection
    | GallerySection
    | FAQSection,
    Field(discriminator="type"),
]


class ProductInfo(ContractModel):
    id: Literal["itmocraft", "joutak", "minigames"]
    canonical_path: str
    requested_path: str
    is_legacy_alias: bool


class LayoutDecision(ContractModel):
    header_variant: Literal["legacy", "v2"]
    footer_variant: Literal["legacy", "v2"]
    default_project: Literal["itmo_craft", "jou_tak", "mini_games"]


class Viewer(ContractModel):
    is_authenticated: bool
    username: str | None = None
    email: str | None = None
    profile_state: str
    profile_complete: bool | None = None
    personalization_context: str | dict[str, object] | None = None


class PageContent(ContractModel):
    template: Literal["landing-legacy", "landing-v2"]
    sections: list[Section]


class PageDocument(ContractModel):
    schema_version: Literal[1] = 1
    product: ProductInfo
    effective_page_variant: Literal["legacy", "v2"]
    variant_source: Literal[
        "default",
        "feature_flag",
        "staff_preview",
        "fixed_legacy",
    ]
    layout: LayoutDecision
    viewer: Viewer
    content: PageContent
