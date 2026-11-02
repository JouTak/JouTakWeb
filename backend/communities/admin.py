from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from communities.models import Community, CommunityMembership


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "visibility")
    search_fields = ("name", "slug")
    list_filter = ("status", "visibility")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CommunityMembership)
class CommunityMembershipAdmin(SimpleHistoryAdmin):
    list_display = ("user", "community", "status", "role", "joined_at")
    search_fields = ("user__username", "community__name")
    list_filter = ("status", "role", "community")
    autocomplete_fields = ("user", "community")
    readonly_fields = ("joined_at", "updated_at")
