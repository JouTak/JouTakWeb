import re
from urllib.parse import urlsplit

from ninja import Schema
from pydantic import Field, model_validator

from profiles.models import ProfileContact
from profiles.schemas import InputSchema
from profiles.validators import Visibility


def normalize_contact(kind, value):
    value = value.strip()
    if value.startswith("https://"):
        url = urlsplit(value)
        hosts = {
            "telegram": {"t.me"},
            "vk": {"vk.com", "vk.ru"},
            "discord": {"discord.com"},
        }
        if (
            url.netloc not in hosts[kind]
            or url.query
            or url.fragment
            or "\\" in value
        ):
            raise ValueError(
                "Укажите ссылку на профиль выбранного сервиса без параметров."
            )
        value = url.path.strip("/")
        if kind == "discord":
            if not re.fullmatch(r"users/[0-9]{10,24}", value):
                raise ValueError(
                    "Укажите имя Discord или ссылку discord.com/users/…"
                )
            return f"https://discord.com/{value}"
    value = value.removeprefix("@")
    pattern = (
        r"[A-Za-z0-9_.-]{1,80}"
        if kind == "discord"
        else r"[A-Za-z0-9_.-]{1,64}"
        if kind == "vk"
        else r"[A-Za-z0-9_]{1,64}"
    )
    if not re.fullmatch(pattern, value):
        raise ValueError("Укажите имя пользователя или ссылку на его профиль.")
    return value


def contact_url(kind, value):
    if kind == "telegram":
        return f"https://t.me/{value}"
    if kind == "vk":
        return f"https://vk.com/{value}"
    return value if value.startswith("https://discord.com/users/") else None


class ContactInput(InputSchema):
    type: ProfileContact.Type
    value: str = Field(min_length=1, max_length=200)
    visibility: Visibility = Visibility.PRIVATE

    @model_validator(mode="after")
    def validate_provider(self):
        self.value = normalize_contact(self.type, self.value)
        return self


class ContactsUpdate(InputSchema):
    version: int = Field(ge=1)
    contacts: list[ContactInput] = Field(max_length=3)

    @model_validator(mode="after")
    def unique_types(self):
        if len({c.type for c in self.contacts}) != len(self.contacts):
            raise ValueError(
                "Добавьте не более одного контакта каждого сервиса."
            )
        return self


class SelfContactsOut(Schema):
    version: int
    contacts: list[ContactInput]
