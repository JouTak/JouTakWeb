from django.contrib import admin

from playergroups.models import (
    GroupAuditEvent,
    GroupContact,
    GroupInvitation,
    GroupJoinRequest,
    GroupLeadershipOffer,
    GroupMembership,
    GroupRestriction,
    PlayerGroup,
)


class ReadOnlyGovernanceAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PlayerGroup)
class PlayerGroupAdmin(ReadOnlyGovernanceAdmin):
    list_display = (
        "name",
        "slug",
        "status",
        "access",
        "join_mode",
        "restricted",
        "scope",
    )
    list_filter = ("status", "access", "restricted", "category")
    search_fields = ("name", "slug")
    # Mutations use the audited product services to preserve invariants.


@admin.register(GroupMembership)
class MembershipAdmin(ReadOnlyGovernanceAdmin):
    list_display = (
        "group",
        "user",
        "role",
        "status",
        "visibility",
        "joined_at",
    )
    list_filter = ("status", "role")
    search_fields = ("group__name", "user__username")


@admin.register(GroupAuditEvent)
class AuditAdmin(ReadOnlyGovernanceAdmin):
    list_display = ("group", "actor", "action", "created_at")
    list_filter = ("action",)
    search_fields = ("group__name",)


for model in (
    GroupContact,
    GroupInvitation,
    GroupJoinRequest,
    GroupLeadershipOffer,
    GroupRestriction,
):
    admin.site.register(model, ReadOnlyGovernanceAdmin)
