from django.contrib import admin

from cities.models import (
    City,
    CityAuditEvent,
    CityContact,
    CityInvitation,
    CityMembership,
    CityRevision,
)


class GovernanceAdmin(admin.ModelAdmin):
    """Inspect in admin; use audited product services for governance writes."""

    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(City)
class CityAdmin(GovernanceAdmin):
    list_display = ("name", "slug", "community", "status", "updated_at")
    list_filter = ("status", "community", "recruitment_status")
    search_fields = ("name", "slug")


@admin.register(CityMembership)
class CityMembershipAdmin(GovernanceAdmin):
    list_display = ("user", "city", "role", "status", "position")
    list_filter = ("role", "status", "city")
    search_fields = ("user__username", "city__name")


@admin.register(CityContact)
class CityContactAdmin(GovernanceAdmin):
    list_display = ("city", "type", "label", "visibility")
    list_filter = ("type", "visibility")
    search_fields = ("label", "city__name")


@admin.register(CityAuditEvent)
class CityAuditEventAdmin(GovernanceAdmin):
    list_display = ("city", "action", "actor", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("city__slug",)


@admin.register(CityRevision)
class CityRevisionAdmin(GovernanceAdmin):
    list_display = ("city", "version", "actor", "created_at")
    search_fields = ("city__slug",)


@admin.register(CityInvitation)
class CityInvitationAdmin(GovernanceAdmin):
    list_display = ("city", "user", "invited_by", "status", "expires_at")
    list_filter = ("status", "city")
    search_fields = ("user__username", "city__name")
