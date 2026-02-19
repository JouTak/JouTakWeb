from __future__ import annotations

from core.models import UserProfile


def missing_personalization_fields(profile: UserProfile) -> list[str]:
    missing: list[str] = []

    if not (profile.vk_username or "").strip():
        missing.append("vk_username")
    if not (profile.minecraft_nick or "").strip():
        missing.append("minecraft_nick")
    if profile.minecraft_has_license is None:
        missing.append("minecraft_has_license")
    if profile.is_itmo_student is None:
        missing.append("is_itmo_student")
    if (
        profile.is_itmo_student is True
        and not (profile.itmo_isu or "").strip()
    ):
        missing.append("itmo_isu")

    return missing


def personalization_complete(profile: UserProfile) -> tuple[bool, list[str]]:
    missing = missing_personalization_fields(profile)
    return (len(missing) == 0), missing
