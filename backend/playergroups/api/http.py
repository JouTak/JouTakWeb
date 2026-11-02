from typing import Annotated

from accounts.transport.schemas import ErrorOut
from communities.access import actor_for, require_flags
from communities.api import PageQuery
from profiles.schemas import Slug
from pydantic import Field

from playergroups.models import PlayerGroup
from playergroups.policies import fail

ERRORS = {
    401: ErrorOut,
    403: ErrorOut,
    404: ErrorOut,
    409: ErrorOut,
    422: ErrorOut,
    429: ErrorOut,
}
Id = Annotated[int, Field(ge=1)]


class Filters(PageQuery):
    q: str = Field(default="", max_length=100)
    scope: Slug | None = None
    category: PlayerGroup.Category | None = None
    join_mode: PlayerGroup.JoinMode | None = None


class AccountFilters(PageQuery):
    history: bool = False


def viewer(request, *, write=False, required=False):
    actor = actor_for(request, required=write or required)
    flags = require_flags(actor, "communities_ui", "player_groups_ui")
    if write and not flags.get("player_groups_write"):
        fail(
            "WRITES_PAUSED",
            "Изменения временно приостановлены. Попробуйте позже.",
            403,
        )
    return actor, flags
