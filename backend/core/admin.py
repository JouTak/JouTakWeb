from __future__ import annotations

from django.contrib import admin

from core.models import UserProfile, UserSessionMeta, UserSessionToken


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "vk_username",
        "minecraft_nick",
        "minecraft_has_license",
        "is_itmo_student",
        "itmo_isu",
        "completed_at",
        "updated_at",
    )
    list_filter = (
        "minecraft_has_license",
        "is_itmo_student",
        "completed_at",
    )
    search_fields = (
        "user__username",
        "user__email",
        "vk_username",
        "minecraft_nick",
        "itmo_isu",
    )
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(UserSessionMeta)
class UserSessionMetaAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "session_key",
        "last_seen",
        "ip",
        "revoked_at",
        "revoked_reason",
    )
    list_filter = ("revoked_at", "first_seen", "last_seen")
    search_fields = (
        "user__username",
        "user__email",
        "session_key",
        "session_token_digest",
        "ip",
    )
    autocomplete_fields = ("user",)
    readonly_fields = (
        "first_seen",
        "last_seen",
        "session_token_digest",
    )


@admin.register(UserSessionToken)
class UserSessionTokenAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "session_key",
        "refresh_jti",
        "created_at",
        "revoked_at",
    )
    list_filter = ("created_at", "revoked_at")
    search_fields = (
        "user__username",
        "user__email",
        "session_key",
        "refresh_jti",
    )
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at",)
