from datetime import datetime
from typing import Literal

from cities.validators import validate_contact
from ninja import Schema
from profiles.schemas import (
    CommunityRef,
    InputSchema,
    SafeUrl,
    Slug,
    Username,
    safe_image,
    safe_url,
)
from pydantic import Field, field_validator, model_validator

from playergroups.models import GroupMembership, PlayerGroup


class ContactIn(InputSchema):
    type: Literal["discord", "telegram", "vk"]
    label: str = Field(min_length=1, max_length=100)
    url: SafeUrl = Field(min_length=1)
    visibility: Literal["public", "members"] = "members"
    _url = field_validator("url")(safe_url)
    _provider = model_validator(mode="after")(validate_contact)


class GroupCreate(InputSchema):
    slug: Slug
    name: str = Field(min_length=1, max_length=120)
    short_description: str = Field(min_length=1, max_length=280)
    category: PlayerGroup.Category = PlayerGroup.Category.CLUB
    scope_slug: Slug | None = None


class GroupUpdate(InputSchema):
    version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    short_description: str | None = Field(
        default=None, min_length=1, max_length=280
    )
    description: str | None = Field(default=None, max_length=12000)
    rules: str | None = Field(default=None, max_length=3000)
    welcome: str | None = Field(default=None, max_length=3000)
    application_question: str | None = Field(default=None, max_length=300)
    logo_url: SafeUrl | None = None
    cover_url: SafeUrl | None = None
    category: PlayerGroup.Category | None = None
    access: PlayerGroup.Access | None = None
    join_mode: PlayerGroup.JoinMode | None = None
    accepting: bool | None = None
    roster_visibility: PlayerGroup.Audience | None = None
    contacts: list[ContactIn] | None = Field(default=None, max_length=8)

    @field_validator("logo_url", "cover_url")
    @classmethod
    def image_reference(cls, value):
        return safe_image(value) if value is not None else value


class LifecycleIn(InputSchema):
    version: int = Field(ge=1)
    action: Literal["publish", "archive", "restore"]


class JoinIn(InputSchema):
    visibility: GroupMembership.Visibility = GroupMembership.Visibility.PRIVATE


class ApplyIn(JoinIn):
    answer: str = Field(default="", max_length=1000)


class InviteIn(InputSchema):
    username: Username


class RespondIn(JoinIn):
    decision: Literal["accept", "decline"]


class ReviewIn(InputSchema):
    decision: Literal["accept", "reject"]
    reason: str = Field(default="", max_length=500)


class RoleIn(InputSchema):
    role: Literal["member", "moderator"]
    reason: str = Field(default="", max_length=500)


class RemoveIn(InputSchema):
    reason: str = Field(default="", max_length=500)


class RestrictionIn(InputSchema):
    active: bool
    until: datetime | None = None
    reason: str = Field(min_length=3, max_length=500)


class OfferIn(InputSchema):
    membership_id: int = Field(ge=1)
    transfer: bool = False


class RecoveryOfferOut(Schema):
    recovery: bool = False


class ModerationIn(InputSchema):
    restricted: bool
    reason: str = Field(min_length=3, max_length=500)


class RecoveryIn(InputSchema):
    username: Username
    reason: str = Field(min_length=3, max_length=500)


class Capabilities(Schema):
    join: bool = False
    apply: bool = False
    edit: bool = False
    manage: bool = False
    configure: bool = False
    moderate: bool = False
    leave: bool = False
    respond: bool = False
    write_enabled: bool = False


class MembershipOut(Schema):
    id: int
    status: GroupMembership.Status
    role: GroupMembership.Role
    visibility: GroupMembership.Visibility
    joined_at: datetime
    eligible: bool


class ProcessOut(RecoveryOfferOut):
    id: int
    kind: Literal["invitation", "request", "leadership"]
    status: Literal[
        "pending",
        "accepted",
        "declined",
        "rejected",
        "cancelled",
        "revoked",
        "expired",
    ]
    created_at: datetime
    expires_at: datetime
    reason: str = ""
    answer: str = ""
    username: str | None = None
    minecraft_nick: str | None = None
    sender_username: str | None = None
    sender_nick: str | None = None
    transfer: bool = False


class GroupRef(Schema):
    slug: str
    name: str
    short_description: str
    logo_url: str
    category: PlayerGroup.Category
    scope: CommunityRef | None
    status: PlayerGroup.Status
    access: PlayerGroup.Access
    join_mode: PlayerGroup.JoinMode
    accepting: bool
    restricted: bool


class GroupCardOut(GroupRef):
    membership: MembershipOut | None = None
    pending: Literal["invitation", "request", "leadership"] | None = None


class GroupListOut(Schema):
    items: list[GroupCardOut]
    total: int
    page: int
    can_create: bool = False
    can_moderate: bool = False


class AccountGroupOut(Schema):
    group: GroupRef | None
    membership: MembershipOut


class AccountGroupListOut(Schema):
    items: list[AccountGroupOut]
    total: int
    page: int


class ViewerOut(Schema):
    state: Literal[
        "guest",
        "eligible",
        "member",
        "scope_required",
        "restricted",
        "inactive",
    ]
    membership: MembershipOut | None = None
    invitation: ProcessOut | None = None
    request: ProcessOut | None = None
    leadership: ProcessOut | None = None


class GroupOut(GroupRef):
    description: str
    rules: str
    welcome: str
    application_question: str
    cover_url: str
    contacts: list[ContactIn]
    roster_visibility: PlayerGroup.Audience
    version: int
    updated_at: datetime
    viewer: ViewerOut
    capabilities: Capabilities


class PersonOut(Schema):
    id: int | None = None
    username: str | None = None
    minecraft_nick: str | None = None
    avatar_url: str | None = None
    role: GroupMembership.Role
    status: GroupMembership.Status
    visibility: GroupMembership.Visibility
    restricted: bool = False
    eligible: bool = True


class PeopleOut(Schema):
    items: list[PersonOut]
    total: int | None
    page: int
    is_visible: bool


class ProcessListOut(Schema):
    items: list[ProcessOut]
    total: int
    page: int


class AccountProcessOut(Schema):
    process: ProcessOut
    group: GroupRef | None
    rules: str = ""


class AccountGroupsOut(Schema):
    memberships: list[GroupCardOut]
    processes: list[AccountProcessOut]
    total: int
    page: int
    write_enabled: bool


class AccountProcessListOut(Schema):
    items: list[AccountProcessOut]
    total: int
    page: int
    write_enabled: bool


class AuditMetadata(Schema):
    platform_override: bool = False
    changed_fields: list[str] = Field(default_factory=list)
    before_role: str | None = None
    after_role: str | None = None
    process_id: int | None = None
    reason: str | None = None
    until: datetime | None = None


class AuditOut(Schema):
    id: int
    action: str
    actor: str | None
    target: str | None
    created_at: datetime
    metadata: AuditMetadata


class AuditListOut(Schema):
    items: list[AuditOut]
    total: int
    page: int
