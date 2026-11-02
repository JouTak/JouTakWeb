from datetime import date, datetime
from typing import Annotated, Literal

from ninja import Schema
from profiles.schemas import (
    CommunityRef,
    InputSchema,
    PublicIdentityOut,
    SafeUrl,
    Slug,
    Username,
    safe_image,
    safe_url,
)
from profiles.validators import Visibility
from pydantic import Field, field_validator, model_validator

from cities.models import City, CityContact, CityMembership
from cities.validators import validate_contact

Coordinate = Annotated[int, Field(strict=True, ge=-30_000_000, le=30_000_000)]


class LocationIn(InputSchema):
    world: str = Field(min_length=1, max_length=80)
    x: Coordinate
    z: Coordinate
    y: Coordinate | None = None
    map_id: str = Field(default="", max_length=80, pattern=r"^[a-zA-Z0-9_-]*$")


class LocationOut(LocationIn):
    map_url: str | None = None


class ContactIn(InputSchema):
    type: CityContact.Type
    label: str = Field(min_length=1, max_length=100)
    url: SafeUrl = Field(min_length=1)
    visibility: Visibility = Visibility.PUBLIC
    _url = field_validator("url")(safe_url)


class ContactWrite(ContactIn):
    type: Literal["discord", "telegram", "vk"]
    _provider = model_validator(mode="after")(validate_contact)


class MapLinkIn(InputSchema):
    url: str = Field(min_length=1, max_length=1500)


class CityContent(InputSchema):
    name: str = Field(min_length=1, max_length=120)
    short_description: str = Field(min_length=1, max_length=280)
    description: str = Field(default="", max_length=12000)
    recruitment_status: City.Recruitment = City.Recruitment.CLOSED
    founded_at: date | None = None
    region: str = Field(default="", max_length=120)
    language: str = Field(default="", max_length=80)
    how_to_join: str = Field(default="", max_length=2000)
    logo_url: SafeUrl = ""
    cover_url: SafeUrl = ""
    location: LocationIn | None = None
    contacts: list[ContactIn] = Field(default_factory=list, max_length=20)
    _urls = field_validator("logo_url", "cover_url")(safe_image)


class CityCreate(CityContent):
    contacts: list[ContactWrite] = Field(default_factory=list, max_length=20)
    community_slug: Slug
    slug: Slug
    manager_username: Username
    status: Literal["draft", "active"] = "draft"


class CityUpdate(InputSchema):
    version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    short_description: str | None = Field(
        default=None, min_length=1, max_length=280
    )
    description: str | None = Field(default=None, max_length=12000)
    recruitment_status: City.Recruitment | None = None
    founded_at: date | None = None
    region: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, max_length=80)
    how_to_join: str | None = Field(default=None, max_length=2000)
    logo_url: SafeUrl | None = None
    cover_url: SafeUrl | None = None
    location: LocationIn | None = None
    contacts: list[ContactWrite] | None = Field(default=None, max_length=20)
    status: City.Status | None = None

    @model_validator(mode="after")
    def reject_null_nonnullable(self):
        for name in self.model_fields_set - {"location", "founded_at"}:
            value = getattr(self, name)
            if value is None:
                raise ValueError(f"{name} не может быть null")
            if name in {"logo_url", "cover_url"}:
                safe_image(value)
        return self


class MemberAdd(InputSchema):
    username: Username
    role: CityMembership.Role = CityMembership.Role.RESIDENT
    position: str = Field(default="", max_length=100)


class MemberUpdate(InputSchema):
    role: CityMembership.Role
    position: str = Field(default="", max_length=100)
    override_reason: str = Field(default="", max_length=500)


class InvitationIn(InputSchema):
    username: Username


class InvitationResponse(InputSchema):
    decision: Literal["accept", "decline"]


class InvitationOut(Schema):
    id: int
    city_slug: str
    city_name: str
    logo_url: str
    username: str
    minecraft_nick: str | None = None
    status: Literal["pending", "accepted", "declined", "revoked"]
    created_at: datetime
    expires_at: datetime


class InvitationListOut(Schema):
    items: list[InvitationOut]
    total: int
    page: int


class Capabilities(Schema):
    edit: bool = False
    manage_location: bool = False
    manage_members: bool = False
    manage_roles: bool = False
    assign_manager: bool = False
    moderate: bool = False


class MembershipVisibilityUpdate(InputSchema):
    visibility: Visibility


class CityCardOut(Schema):
    slug: str
    name: str
    short_description: str
    logo_url: str
    status: City.Status
    recruitment_status: City.Recruitment
    community: CommunityRef
    member_count: int
    updated_at: datetime


class LeadershipOut(PublicIdentityOut):
    role: CityMembership.Role
    position: str


class CityLeaderOut(Schema):
    username: str
    minecraft_nick: str | None = None
    position: str


class CatalogCityOut(CityCardOut):
    leader: CityLeaderOut | None = None
    map_url: str | None = None


class ResidentsOut(Schema):
    items: list[LeadershipOut]
    total: int
    page: int


class CityDetailOut(CityCardOut):
    description: str
    founded_at: date | None
    region: str
    language: str
    how_to_join: str
    cover_url: str
    location: LocationOut | None
    contacts: list[ContactIn]
    leadership: list[LeadershipOut]
    capabilities: Capabilities
    version: int
    published_at: datetime | None


class CityListOut(Schema):
    items: list[CatalogCityOut]
    total: int
    page: int


class MemberOut(Schema):
    id: int
    username: str
    minecraft_nick: str | None = None
    avatar_url: str | None = None
    role: CityMembership.Role
    position: str
    status: CityMembership.Status
    visibility: Visibility = Visibility.COMMUNITY


class MemberListOut(Schema):
    items: list[MemberOut]
    total: int
    page: int


class OwnMembershipOut(Schema):
    membership: MemberOut | None


class AuditMetadata(Schema):
    invitation_id: int | None = None
    changed_fields: list[str] = Field(default_factory=list)
    before_role: str | None = None
    after_role: str | None = None
    before_status: str | None = None
    after_status: str | None = None
    override_reason: str | None = None
    before_position: str | None = None
    after_position: str | None = None
    before_visibility: Visibility | None = None
    after_visibility: Visibility | None = None


class AuditOut(Schema):
    target_username: str | None = None
    id: int
    action: str
    actor: str | None
    created_at: datetime
    metadata: AuditMetadata


class RevisionContent(CityContent):
    status: City.Status | None = None


class RevisionOut(Schema):
    version: int
    actor: str | None
    created_at: datetime
    changed_fields: list[str]
    content: RevisionContent


class HistoryOut(Schema):
    events: list[AuditOut]
    revisions: list[RevisionOut]
    page: int


class ModerationCityOut(CityCardOut):
    managers: list[str]
    updated_by: str | None
    visibility: Visibility


class ModerationListOut(Schema):
    items: list[ModerationCityOut]
    total: int
    page: int
