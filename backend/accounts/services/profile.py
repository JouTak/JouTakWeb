from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Never
from uuid import uuid4

from accounts.services.personalization import personalization_complete
from core.models import UserProfile
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import UploadedFile
from django.core.files.utils import validate_file_name
from django.db import transaction
from django.utils import timezone
from ninja.errors import HttpError
from PIL import Image, UnidentifiedImageError

User = get_user_model()
VK_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{2,64}$")
MINECRAFT_NICK_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")
ITMO_ISU_RE = re.compile(r"^\d{5,20}$")
AVATAR_ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
AVATAR_FORMAT_EXTENSIONS = {
    "JPEG": "jpg",
    "PNG": "png",
    "WEBP": "webp",
}
DEFAULT_AVATAR_MAX_UPLOAD_BYTES = 2 * 1024 * 1024


@dataclass(slots=True)
class ProfileService:
    @staticmethod
    def _raise_field_error(
        field: str, message: str, code: str = "invalid"
    ) -> Never:
        raise HttpError(
            400,
            json.dumps(
                {field: [{"message": message, "code": code}]},
                ensure_ascii=False,
            ),
        )

    @staticmethod
    def get_or_create_extended_profile(user: User) -> UserProfile:
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return profile

    @staticmethod
    def serialize_extended_profile(profile: UserProfile) -> dict:
        return {
            "vk_username": profile.vk_username or None,
            "minecraft_nick": profile.minecraft_nick or None,
            "minecraft_has_license": profile.minecraft_has_license,
            "is_itmo_student": profile.is_itmo_student,
            "itmo_isu": profile.itmo_isu or None,
        }

    @staticmethod
    def normalize_vk_username(raw: str) -> str:
        value = (raw or "").strip()
        lowered = value.lower()
        for prefix in (
            "https://vk.com/",
            "http://vk.com/",
            "https://m.vk.com/",
            "http://m.vk.com/",
            "vk.com/",
            "m.vk.com/",
        ):
            if lowered.startswith(prefix):
                value = value[len(prefix) :]
                break
        return value.strip().lstrip("@").strip().strip("/")

    @staticmethod
    def _apply_vk_username(
        profile: UserProfile,
        vk_username: str,
        to_update: list[str],
    ) -> None:
        normalized = ProfileService.normalize_vk_username(vk_username)
        if normalized and not VK_USERNAME_RE.fullmatch(normalized):
            ProfileService._raise_field_error(
                "vk_username", "Некорректный username VK"
            )
        profile.vk_username = normalized
        to_update.append("vk_username")

    @staticmethod
    def _apply_minecraft_nick(
        profile: UserProfile,
        minecraft_nick: str,
        to_update: list[str],
    ) -> None:
        normalized = (minecraft_nick or "").strip()
        if normalized and not MINECRAFT_NICK_RE.fullmatch(normalized):
            ProfileService._raise_field_error(
                "minecraft_nick",
                (
                    "Ник Minecraft должен быть 3-16 символов: "
                    "латиница, цифры, _"
                ),
            )
        profile.minecraft_nick = normalized
        to_update.append("minecraft_nick")

    @staticmethod
    def _apply_is_itmo_student(
        profile: UserProfile,
        *,
        is_itmo_student: bool,
        to_update: list[str],
    ) -> None:
        profile.is_itmo_student = bool(is_itmo_student)
        to_update.append("is_itmo_student")
        if not profile.is_itmo_student:
            profile.itmo_isu = None
            to_update.append("itmo_isu")

    @staticmethod
    def _apply_itmo_isu(
        profile: UserProfile,
        itmo_isu: str,
        to_update: list[str],
    ) -> None:
        normalized = (itmo_isu or "").strip()
        if profile.is_itmo_student is False:
            profile.itmo_isu = None
            to_update.append("itmo_isu")
            return
        if normalized and not ITMO_ISU_RE.fullmatch(normalized):
            ProfileService._raise_field_error(
                "itmo_isu", "ИСУ должен содержать только цифры (5-20)"
            )
        profile.itmo_isu = normalized or None
        to_update.append("itmo_isu")

    @staticmethod
    def _normalize_name(
        user: User,
        *,
        field_name: str,
        raw_value: str | None,
    ) -> str:
        normalized = (raw_value or "").strip()
        max_length = user._meta.get_field(field_name).max_length
        if max_length is not None and len(normalized) > max_length:
            ProfileService._raise_field_error(
                field_name,
                f"Максимальная длина: {max_length}",
                code="max_length",
            )
        return normalized

    @staticmethod
    @transaction.atomic
    def update_profile_fields(
        user: User,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        vk_username: str | None = None,
        minecraft_nick: str | None = None,
        minecraft_has_license: bool | None = None,
        is_itmo_student: bool | None = None,
        itmo_isu: str | None = None,
    ) -> UserProfile:
        ProfileService.update_name(user, first=first_name, last=last_name)
        profile = ProfileService.get_or_create_extended_profile(user)
        to_update: list[str] = []

        if vk_username is not None:
            ProfileService._apply_vk_username(profile, vk_username, to_update)

        if minecraft_nick is not None:
            ProfileService._apply_minecraft_nick(
                profile, minecraft_nick, to_update
            )

        if minecraft_has_license is not None:
            profile.minecraft_has_license = bool(minecraft_has_license)
            to_update.append("minecraft_has_license")

        if is_itmo_student is not None:
            ProfileService._apply_is_itmo_student(
                profile,
                is_itmo_student=is_itmo_student,
                to_update=to_update,
            )

        if itmo_isu is not None:
            ProfileService._apply_itmo_isu(profile, itmo_isu, to_update)

        complete, _ = personalization_complete(profile)
        if complete and not profile.completed_at:
            profile.completed_at = timezone.now()
            to_update.append("completed_at")

        if to_update:
            profile.save(update_fields=sorted({*to_update, "updated_at"}))
        return profile

    @staticmethod
    @transaction.atomic
    def update_name(
        user: User, *, first: str | None = None, last: str | None = None
    ) -> None:
        to_update: list[str] = []
        if first is not None:
            user.first_name = ProfileService._normalize_name(
                user,
                field_name="first_name",
                raw_value=first,
            )
            to_update.append("first_name")
        if last is not None:
            user.last_name = ProfileService._normalize_name(
                user,
                field_name="last_name",
                raw_value=last,
            )
            to_update.append("last_name")
        if to_update:
            user.save(update_fields=to_update)

    @staticmethod
    def _validate_avatar_upload(avatar: UploadedFile) -> str:
        max_size = getattr(
            settings,
            "AVATAR_MAX_UPLOAD_BYTES",
            DEFAULT_AVATAR_MAX_UPLOAD_BYTES,
        )
        if avatar.size and avatar.size > max_size:
            raise HttpError(400, "avatar file is too large")

        content_type = (getattr(avatar, "content_type", "") or "").lower()
        if content_type not in AVATAR_ALLOWED_CONTENT_TYPES:
            raise HttpError(400, "unsupported avatar content type")

        try:
            avatar.seek(0)
            with Image.open(avatar) as image:
                image.verify()
                extension = AVATAR_FORMAT_EXTENSIONS.get(image.format or "")
        except (OSError, SyntaxError, UnidentifiedImageError) as exc:
            raise HttpError(400, "invalid avatar image") from exc
        finally:
            avatar.seek(0)

        if not extension:
            raise HttpError(400, "unsupported avatar image format")
        return extension

    @staticmethod
    def save_avatar(user: User, avatar: UploadedFile) -> bool:
        if hasattr(user, "avatar"):
            extension = ProfileService._validate_avatar_upload(avatar)
            safe_name = validate_file_name(
                f"avatar-{uuid4().hex}.{extension}"
            )
            user.avatar.save(safe_name, avatar)
            user.save(update_fields=["avatar"])
            return True
        return False
