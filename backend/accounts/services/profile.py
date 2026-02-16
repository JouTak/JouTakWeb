from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from accounts.services.personalization import personalization_complete
from core.models import UserProfile
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone
from ninja.errors import HttpError

User = get_user_model()
VK_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{2,64}$")
MINECRAFT_NICK_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")
ITMO_ISU_RE = re.compile(r"^\d{5,20}$")


@dataclass(slots=True)
class ProfileService:
    @staticmethod
    def _raise_field_error(field: str, message: str, code: str = "invalid"):
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
    @transaction.atomic
    def update_profile_fields(
        user: User,
        *,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        vk_username: Optional[str] = None,
        minecraft_nick: Optional[str] = None,
        minecraft_has_license: Optional[bool] = None,
        is_itmo_student: Optional[bool] = None,
        itmo_isu: Optional[str] = None,
    ) -> UserProfile:
        ProfileService.update_name(user, first=first_name, last=last_name)
        profile = ProfileService.get_or_create_extended_profile(user)
        to_update: list[str] = []

        if vk_username is not None:
            normalized = ProfileService.normalize_vk_username(vk_username)
            if normalized and not VK_USERNAME_RE.fullmatch(normalized):
                ProfileService._raise_field_error(
                    "vk_username", "Некорректный username VK"
                )
            profile.vk_username = normalized
            to_update.append("vk_username")

        if minecraft_nick is not None:
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

        if minecraft_has_license is not None:
            profile.minecraft_has_license = bool(minecraft_has_license)
            to_update.append("minecraft_has_license")

        if is_itmo_student is not None:
            profile.is_itmo_student = bool(is_itmo_student)
            to_update.append("is_itmo_student")
            if not profile.is_itmo_student:
                profile.itmo_isu = None
                to_update.append("itmo_isu")

        if itmo_isu is not None:
            normalized = (itmo_isu or "").strip()
            if profile.is_itmo_student is False:
                profile.itmo_isu = None
                to_update.append("itmo_isu")
            elif normalized and not ITMO_ISU_RE.fullmatch(normalized):
                ProfileService._raise_field_error(
                    "itmo_isu", "ИСУ должен содержать только цифры (5-20)"
                )
            else:
                profile.itmo_isu = normalized or None
                to_update.append("itmo_isu")

        complete, _ = personalization_complete(profile)
        if complete and not profile.completed_at:
            profile.completed_at = timezone.now()
            to_update.append("completed_at")

        if to_update:
            profile.save(update_fields=sorted(set(to_update + ["updated_at"])))
        return profile

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
