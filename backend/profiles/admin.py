from django.contrib import admin

from profiles.models import CommunityProfile, ProfileContact, ProfileFollow


@admin.register(CommunityProfile)
class CommunityProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "visibility", "updated_at")
    search_fields = ("user__username", "display_name")
    list_filter = ("visibility",)
    autocomplete_fields = ("user",)
    readonly_fields = ("updated_at", "minecraft_first_joined_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProfileContact)
class ProfileContactAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "visibility", "updated_at")
    list_filter = ("type", "visibility")
    search_fields = ("user__username",)
    readonly_fields = ("user", "type", "value", "visibility", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProfileFollow)
class ProfileFollowAdmin(admin.ModelAdmin):
    list_display = ("user", "target", "created_at")
    search_fields = ("user__username", "target__username")
    readonly_fields = ("user", "target", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
