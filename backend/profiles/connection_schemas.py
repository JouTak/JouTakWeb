from typing import Literal

from ninja import Schema
from pydantic import Field

from profiles.schemas import InputSchema, PublicIdentityOut


class FollowInput(InputSchema):
    pass


class FollowOut(Schema):
    is_following: bool


class PlayerCityOut(Schema):
    slug: str
    name: str
    role: Literal["resident", "representative", "manager"]
    position: str


class PlayerOut(PublicIdentityOut):
    bio: str
    cities: list[PlayerCityOut] = Field(default_factory=list)
    is_following: bool = False
    is_self: bool = False


class PlayersOut(Schema):
    items: list[PlayerOut]
    total: int
    page: int
    is_visible: bool = True


class PlayerFilters(Schema):
    q: str = Field(default="", max_length=100)
    page: int = Field(default=1, ge=1, le=1000)
    following: bool = False


class ConnectionFilters(Schema):
    direction: Literal["following", "followers", "friends"] = "following"
    page: int = Field(default=1, ge=1, le=1000)
