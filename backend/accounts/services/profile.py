from __future__ import annotations
from typing import Optional
from dataclasses import dataclass
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.files.uploadedfile import UploadedFile

User = get_user_model()


@dataclass(slots=True)
class ProfileService:

    @staticmethod
    @transaction.atomic
    def update_name(
        user: User, *, first: Optional[str] = None, last: Optional[str] = None
    ) -> None:
        to_update: list[str] = []
        if first is not None:
            user.first_name = (first or "").strip()
            to_update.append("first_name")
        if last is not None:
            user.last_name = (last or "").strip()
            to_update.append("last_name")
        if to_update:
            user.save(update_fields=to_update)

    @staticmethod
    def save_avatar(user: User, avatar: UploadedFile) -> bool:
        if hasattr(user, "avatar"):
            user.avatar.save(avatar.name, avatar)
            user.save(update_fields=["avatar"])
            return True
        return False
