from ninja import Schema
from profiles.schemas import CommunityMembershipOut, CommunityRef


class CommunityOut(CommunityRef):
    short_description: str
    description: str
    logo_url: str
    cover_url: str
    member_count: int
    has_cities: bool = False
    enrollment_text: str = ""
    enrollment_url: str = ""
    membership: CommunityMembershipOut | None = None


class ServerMembershipsOut(Schema):
    items: list[CommunityMembershipOut]


class CommunityListOut(Schema):
    items: list[CommunityOut]
    total: int
    page: int
