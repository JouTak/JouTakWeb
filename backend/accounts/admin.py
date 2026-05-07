from __future__ import annotations

import csv
import logging
from urllib.parse import urlencode

from accounts.services.email_addresses import sync_user_email_address
from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from allauth.usersessions.models import UserSession
from core.models import UserProfile, UserSessionMeta, UserSessionToken
from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Count, Exists, OuterRef, Q
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import urlencode as django_urlencode

logger = logging.getLogger(__name__)

User = get_user_model()


def _mask_secret(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "missing"
    if len(raw) <= 6:
        return "configured"
    return f"{raw[:3]}...{raw[-3:]}"


def _safe_unregister(model) -> None:
    try:
        admin.site.unregister(model)
    except NotRegistered:
        logger.debug("%s admin was not registered before override", model)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    extra = 0
    can_delete = False
    fields = (
        "vk_username",
        "minecraft_nick",
        "minecraft_has_license",
        "is_itmo_student",
        "itmo_isu",
        "completed_at",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")
    show_change_link = True


class EmailAddressInline(admin.TabularInline):
    model = EmailAddress
    extra = 0
    fields = ("email", "verified", "primary")
    show_change_link = True


class SocialAccountInline(admin.TabularInline):
    model = SocialAccount
    extra = 0
    fields = ("provider", "uid", "last_login", "date_joined")
    readonly_fields = ("provider", "uid", "last_login", "date_joined")
    can_delete = False
    show_change_link = True


class AuthenticatorInline(admin.TabularInline):
    model = Authenticator
    extra = 0
    fields = ("type", "created_at", "last_used_at")
    readonly_fields = ("type", "created_at", "last_used_at")
    can_delete = False
    show_change_link = True


class UserSessionMetaInline(admin.TabularInline):
    model = UserSessionMeta
    extra = 0
    fields = ("session_key", "ip", "last_seen", "revoked_at", "revoked_reason")
    readonly_fields = (
        "session_key",
        "ip",
        "last_seen",
        "revoked_at",
        "revoked_reason",
    )
    can_delete = False
    show_change_link = True


class UserSessionTokenInline(admin.TabularInline):
    model = UserSessionToken
    extra = 0
    fields = ("session_key", "refresh_jti", "created_at", "revoked_at")
    readonly_fields = (
        "session_key",
        "refresh_jti",
        "created_at",
        "revoked_at",
    )
    can_delete = False
    show_change_link = True


class EmailVerifiedFilter(admin.SimpleListFilter):
    title = "email verified"
    parameter_name = "email_verified"

    def lookups(self, request, model_admin):
        return (("yes", "Verified"), ("no", "Not verified"))

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(primary_email_verified=True)
        if self.value() == "no":
            return queryset.filter(primary_email_verified=False)
        return queryset


class ProfileCompleteFilter(admin.SimpleListFilter):
    title = "profile complete"
    parameter_name = "profile_complete"

    def lookups(self, request, model_admin):
        return (("yes", "Complete"), ("no", "Incomplete"))

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(profile_completed=True)
        if self.value() == "no":
            return queryset.filter(profile_completed=False)
        return queryset


class OAuthPresenceFilter(admin.SimpleListFilter):
    title = "oauth connected"
    parameter_name = "oauth_connected"

    def lookups(self, request, model_admin):
        return (("yes", "Connected"), ("no", "Not connected"))

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(oauth_provider_count__gt=0)
        if self.value() == "no":
            return queryset.filter(oauth_provider_count=0)
        return queryset


class ActiveSessionFilter(admin.SimpleListFilter):
    title = "active sessions"
    parameter_name = "active_sessions"

    def lookups(self, request, model_admin):
        return (("yes", "Has active"), ("no", "No active"))

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(active_session_count__gt=0)
        if self.value() == "no":
            return queryset.filter(active_session_count=0)
        return queryset


def export_users_csv(modeladmin, request, queryset) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="users.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "id",
            "username",
            "email",
            "is_active",
            "is_staff",
            "email_verified",
            "profile_completed",
            "vk_username",
            "minecraft_nick",
            "is_itmo_student",
            "itmo_isu",
        ]
    )
    for user in queryset.select_related("extended_profile"):
        profile = getattr(user, "extended_profile", None)
        writer.writerow(
            [
                user.pk,
                user.username,
                user.email,
                user.is_active,
                user.is_staff,
                bool(getattr(user, "primary_email_verified", False)),
                bool(getattr(user, "profile_completed", False)),
                getattr(profile, "vk_username", ""),
                getattr(profile, "minecraft_nick", ""),
                getattr(profile, "is_itmo_student", ""),
                getattr(profile, "itmo_isu", ""),
            ]
        )
    return response


export_users_csv.short_description = "Export selected users to CSV"


for model in (
    User,
    EmailAddress,
    SocialAccount,
    SocialApp,
    SocialToken,
    Authenticator,
    UserSession,
):
    _safe_unregister(model)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    actions = (export_users_csv,)
    inlines = (
        UserProfileInline,
        EmailAddressInline,
        SocialAccountInline,
        AuthenticatorInline,
        UserSessionMetaInline,
        UserSessionTokenInline,
    )
    list_display = (
        "username",
        "email",
        "is_active",
        "is_staff",
        "email_verified",
        "profile_state",
        "oauth_providers",
        "active_sessions",
        "last_login",
        "date_joined",
    )
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        EmailVerifiedFilter,
        ProfileCompleteFilter,
        OAuthPresenceFilter,
        ActiveSessionFilter,
        "extended_profile__is_itmo_student",
        "extended_profile__minecraft_has_license",
    )
    search_fields = (
        "username",
        "email",
        "extended_profile__vk_username",
        "extended_profile__minecraft_nick",
        "extended_profile__itmo_isu",
        "session_meta__session_key",
        "session_tokens__refresh_jti",
    )
    readonly_fields = (
        "date_joined",
        "last_login",
        "backoffice_summary",
        "linked_operations",
    )
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "Backoffice",
            {
                "fields": (
                    "backoffice_summary",
                    "linked_operations",
                )
            },
        ),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        verified_email = EmailAddress.objects.filter(
            user=OuterRef("pk"),
            email__iexact=OuterRef("email"),
            verified=True,
        )
        return (
            queryset.select_related("extended_profile")
            .annotate(
                oauth_provider_count=Count("socialaccount", distinct=True),
                active_session_count=Count(
                    "session_tokens",
                    filter=Q(session_tokens__revoked_at__isnull=True),
                    distinct=True,
                ),
                profile_completed=Exists(
                    UserProfile.objects.filter(
                        user=OuterRef("pk"),
                        completed_at__isnull=False,
                    )
                ),
                primary_email_verified=Exists(verified_email),
            )
            .distinct()
        )

    @admin.display(boolean=True, ordering="primary_email_verified")
    def email_verified(self, obj) -> bool:
        return bool(getattr(obj, "primary_email_verified", False))

    @admin.display(description="Profile state", ordering="profile_completed")
    def profile_state(self, obj) -> str:
        profile = getattr(obj, "extended_profile", None)
        if profile and profile.completed_at:
            return "complete"
        if profile:
            return "started"
        return "missing"

    @admin.display(description="OAuth", ordering="oauth_provider_count")
    def oauth_providers(self, obj) -> str:
        providers = list(
            obj.socialaccount_set.order_by("provider").values_list(
                "provider", flat=True
            )
        )
        return ", ".join(providers) if providers else "none"

    @admin.display(
        description="Active sessions",
        ordering="active_session_count",
    )
    def active_sessions(self, obj) -> int:
        return int(getattr(obj, "active_session_count", 0))

    @admin.display(description="Backoffice summary")
    def backoffice_summary(self, obj) -> str:
        profile = getattr(obj, "extended_profile", None)
        if profile is None:
            return "No profile yet."
        return (
            f"VK: {profile.vk_username or '-'} | "
            f"Minecraft: {profile.minecraft_nick or '-'} | "
            f"ITMO: {profile.itmo_isu or '-'}"
        )

    @admin.display(description="Related views")
    def linked_operations(self, obj) -> str:
        profile_url = (
            reverse("admin:core_userprofile_changelist")
            + "?"
            + urlencode({"user__id__exact": obj.pk})
        )
        sessions_url = (
            reverse("admin:core_usersessionmeta_changelist")
            + "?"
            + urlencode({"user__id__exact": obj.pk})
        )
        feature_overrides_url = (
            reverse("admin:featureflags_featureoverride_changelist")
            + "?"
            + django_urlencode({"scope_value": obj.pk})
        )
        return format_html(
            '<a href="{}">Profile</a> | <a href="{}">Sessions</a> | '
            '<a href="{}">Feature overrides</a>',
            profile_url,
            sessions_url,
            feature_overrides_url,
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        sync_user_email_address(obj)


@admin.register(EmailAddress)
class EmailAddressAdmin(admin.ModelAdmin):
    list_display = ("email", "user", "verified", "primary")
    list_filter = ("verified", "primary")
    search_fields = ("email", "user__username", "user__email")
    autocomplete_fields = ("user",)


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "uid", "last_login", "date_joined")
    list_filter = ("provider",)
    search_fields = ("uid", "user__username", "user__email")
    autocomplete_fields = ("user",)
    readonly_fields = ("last_login", "date_joined", "extra_data")


@admin.register(SocialApp)
class SocialAppAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "provider_id", "client_id")
    search_fields = ("name", "provider", "provider_id", "client_id")


@admin.register(SocialToken)
class SocialTokenAdmin(admin.ModelAdmin):
    list_display = ("account", "app", "expires_at", "token_state")
    search_fields = (
        "account__user__username",
        "account__user__email",
        "account__uid",
    )
    autocomplete_fields = ("account", "app")
    readonly_fields = ("masked_token", "masked_token_secret")

    @admin.display(description="Token")
    def token_state(self, obj) -> str:
        return "configured" if obj.token else "missing"

    @admin.display(description="Access token")
    def masked_token(self, obj) -> str:
        return _mask_secret(obj.token)

    @admin.display(description="Token secret")
    def masked_token_secret(self, obj) -> str:
        return _mask_secret(obj.token_secret)


@admin.register(Authenticator)
class AuthenticatorAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "created_at", "last_used_at")
    list_filter = ("type", "created_at", "last_used_at")
    search_fields = ("user__username", "user__email")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "last_used_at")


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "session_key", "ip", "last_seen_at", "created_at")
    list_filter = ("created_at", "last_seen_at")
    search_fields = ("user__username", "user__email", "session_key", "ip")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "last_seen_at", "data_state")

    @admin.display(description="Session payload")
    def data_state(self, obj) -> str:
        return "present" if obj.data else "empty"
