from ninja.errors import HttpError

from profiles.schemas import ProfilePreviewOut
from profiles.services import public_profile


def guest_preview(actor):
    try:
        return ProfilePreviewOut(profile=public_profile(actor.username, None))
    except HttpError as exc:
        if exc.status_code != 404:
            raise
        return ProfilePreviewOut(profile=None)
