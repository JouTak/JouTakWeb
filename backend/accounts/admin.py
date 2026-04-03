from __future__ import annotations

from accounts.services.email_addresses import sync_user_email_address
from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

User = get_user_model()


try:
    admin.site.unregister(User)
except NotRegistered:
    # The auth user model may be absent in admin at startup in some envs.
    # Re-register below with our custom admin class.
    pass


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        sync_user_email_address(obj)
