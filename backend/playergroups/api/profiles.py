from communities.api import PageQuery
from ninja import Query, Router
from profiles.schemas import Username

from playergroups import (
    account,
)
from playergroups.schemas import (
    GroupListOut,
)

from .http import ERRORS, viewer

router = Router(tags=["Player groups"])


@router.get(
    "/public/{username}/groups", response={200: GroupListOut, **ERRORS}
)
def profile_groups(request, username: Username, filters: Query[PageQuery]):
    actor, _ = viewer(request)
    return account.profile_groups(actor, username, filters.page)
