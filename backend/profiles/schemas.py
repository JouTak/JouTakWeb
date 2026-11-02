from datetime import date, datetime
from typing import Annotated, Literal

from django.core.exceptions import ValidationError as DjangoValidationError
from ninja import Schema
from pydantic import ConfigDict, Field, field_validator, model_validator

from profiles.validators import (
    Visibility,
    validate_image_reference,
    validate_safe_url,
)


class InputSchema(Schema):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


SafeUrl = Annotated[str, Field(max_length=500)]
Username = Annotated[str, Field(min_length=1, max_length=150)]
Slug = Annotated[
    str,
    Field(min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
]


def safe_url(value):
    try:
        validate_safe_url(value)
    except DjangoValidationError as exc:
        raise ValueError("Используйте безопасный HTTPS URL.") from exc
    return value


def safe_image(value):
    try:
        validate_image_reference(value)
    except DjangoValidationError as exc:
        raise ValueError(
            "Загрузите изображение или укажите HTTPS-ссылку."
        ) from exc
    return value


class ProfileUpdate(InputSchema):
    version: int = Field(ge=1)
    display_name: str | None = Field(default=None, max_length=100)
    bio: str | None = Field(default=None, max_length=2000)
    avatar_url: SafeUrl | None = None
    visibility: Visibility | None = None
    minecraft_visibility: Visibility | None = None
    social_visibility: Visibility | None = None
    itmo_visibility: Visibility | None = None
    memberships_visibility: Visibility | None = None
    connections_visibility: Visibility | None = None

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar(cls, value):
        if value is None:
            raise ValueError("Для удаления аватара используйте пустую строку.")
        return safe_image(value)

    @model_validator(mode="after")
    def reject_null(self):
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Для очистки текста используйте пустую строку.")
        return self


class PublicIdentityOut(Schema):
    username: str | None = None
    display_name: str
    avatar_url: str | None = None
    minecraft_nick: str | None = None


class CommunityRef(Schema):
    slug: str
    name: str


class CommunityMembershipOut(Schema):
    community: CommunityRef
    role: str
    status: str
    joined_at: datetime


class CityMembershipOut(Schema):
    slug: str
    name: str
    logo_url: str = ""
    short_description: str = ""
    community: CommunityRef
    status: str
    city_status: Literal["draft", "active", "archived"]
    role: str
    position: str
    visibility: Visibility
    joined_at: datetime
    can_manage: bool = False


class MembershipsOut(Schema):
    communities: list[CommunityMembershipOut]
    cities: list[CityMembershipOut]


class ProfileContactOut(Schema):
    type: Literal["discord", "telegram", "vk"]
    value: str
    url: str | None = None


class ServerHistoryOut(Schema):
    first_joined_on: date
    days: int = Field(ge=0)
    days_text: str


class PublicProfileOut(PublicIdentityOut):
    is_self: bool = False
    is_following: bool = False
    contacts: list[ProfileContactOut] = Field(default_factory=list)
    bio: str
    vk_url: str | None = None
    itmo_student: bool | None = None
    joined_at: datetime
    server_history: ServerHistoryOut | None = None
    memberships: MembershipsOut
    own_visibility: Visibility | None = None


class SelfProfileOut(PublicProfileOut):
    version: int
    visibility: Visibility
    minecraft_visibility: Visibility
    social_visibility: Visibility
    itmo_visibility: Visibility
    memberships_visibility: Visibility
    connections_visibility: Visibility
    can_moderate: bool


class ProfilePreviewOut(Schema):
    profile: PublicProfileOut | None
