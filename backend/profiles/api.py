from accounts.transport.schemas import ErrorOut
from communities.access import actor_for, require_flags
from ninja import File, Router, UploadedFile

from profiles.media import ImageOut, upload_image
from profiles.schemas import (
    ProfileUpdate,
    PublicProfileOut,
    SelfProfileOut,
    Username,
)
from profiles.services import profile_out, public_profile, update_profile

router = Router(tags=["Community profiles"])
ERRORS = {
    401: ErrorOut,
    403: ErrorOut,
    404: ErrorOut,
    409: ErrorOut,
    422: ErrorOut,
}


@router.post("/images", response={200: ImageOut, 429: ErrorOut, **ERRORS})
def upload_profile_image(request, file: File[UploadedFile]):
    actor = actor_for(request, required=True)
    require_flags(actor, "community_profiles_ui")
    return upload_image(request, actor, file)


@router.get("/me", response={200: SelfProfileOut, **ERRORS}, exclude_none=True)
def self_profile(request):
    actor = actor_for(request, required=True)
    require_flags(actor, "community_profiles_ui")
    return profile_out(actor, actor, self_view=True)


@router.patch(
    "/me", response={200: SelfProfileOut, **ERRORS}, exclude_none=True
)
def save_profile(request, payload: ProfileUpdate):
    actor = actor_for(request, required=True)
    require_flags(actor, "community_profiles_ui")
    return update_profile(actor, payload)


@router.get(
    "/public/{username}",
    response={200: PublicProfileOut, **ERRORS},
    exclude_none=True,
)
def get_public_profile(request, username: Username):
    actor = actor_for(request)
    require_flags(actor, "community_profiles_ui")
    return public_profile(username, actor)
