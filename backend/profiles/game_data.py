from accounts.services.profile import ProfileService
from django.contrib.auth import get_user_model
from django.db import transaction
from ninja import Schema
from pydantic import Field, model_validator

from profiles.editing import check_version
from profiles.schemas import InputSchema


class GameDataUpdate(InputSchema):
    version: str = Field(min_length=20, max_length=40)
    minecraft_nick: str | None = Field(default=None, max_length=16)
    minecraft_has_license: bool | None = None
    vk_username: str | None = Field(default=None, max_length=100)
    is_itmo_student: bool | None = None
    itmo_isu: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def reject_null(self):
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError(
                "Пропустите неизменяемое поле; текст очищается пустой строкой."
            )
        return self


class GameDataOut(Schema):
    username: str
    version: str
    minecraft_nick: str | None
    minecraft_has_license: bool | None
    vk_username: str | None
    is_itmo_student: bool | None
    itmo_isu: str | None


def read_game_data(user):
    profile = ProfileService.get_or_create_extended_profile(user)
    return GameDataOut(
        username=user.username,
        version=profile.updated_at.isoformat(),
        **ProfileService.serialize_extended_profile(profile),
    )


@transaction.atomic
def save_game_data(user, payload):
    user = get_user_model().objects.select_for_update().get(pk=user.pk)
    profile = ProfileService.get_or_create_extended_profile(user)
    check_version(profile.updated_at.isoformat(), payload.version)
    ProfileService.update_profile_fields(
        user, **payload.model_dump(exclude_unset=True, exclude={"version"})
    )
    return read_game_data(user)
