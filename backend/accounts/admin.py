from __future__ import annotations

import csv
import logging

from accounts.services.email_addresses import sync_user_email_address
from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from allauth.socialaccount.models import (
    SocialAccount,
    SocialApp,
    SocialToken,
)
from allauth.usersessions.models import UserSession
from axes.models import AccessAttempt, AccessFailureLog, AccessLog
from core.models import UserProfile, UserSessionMeta, UserSessionToken
from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.core.exceptions import PermissionDenied
from django.db.models import Exists, OuterRef
from django.http import HttpResponse
from django.utils import formats, timezone
from django.utils.html import format_html
from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken

logger = logging.getLogger(__name__)

User = get_user_model()

_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")
_PRIVILEGE_FIELDS = (
    "is_staff",
    "is_superuser",
    "groups",
    "user_permissions",
)


def _safe_unregister(model) -> None:
    try:
        admin.site.unregister(model)
    except NotRegistered:
        logger.debug("%s admin was not registered before override", model)


def _csv_safe_text(value: object) -> str:
    """Prevent spreadsheet clients from interpreting exported text as code."""
    raw = str(value or "")
    stripped = raw.lstrip(" \t\r\n")
    if raw.startswith(_CSV_FORMULA_PREFIXES) or stripped.startswith(
        _CSV_FORMULA_PREFIXES[:4]
    ):
        return f"'{raw}"
    return raw


def _admin_datetime(value) -> str:
    if value is None:
        return "never"
    return formats.date_format(
        timezone.localtime(value),
        "SHORT_DATETIME_FORMAT",
    )


class UserProfileInline(admin.StackedInline):
    """The only editable account extension in the canonical user card."""

    model = UserProfile
    extra = 1
    max_num = 1
    can_delete = False
    show_change_link = False
    fields = (
        ("vk_username", "minecraft_nick"),
        ("minecraft_has_license", "is_itmo_student"),
        ("itmo_isu", "completed_at"),
        ("created_at", "updated_at"),
    )
    readonly_fields = ("created_at", "updated_at")


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


@admin.action(description="Export selected users to CSV")
def export_users_csv(modeladmin, request, queryset) -> HttpResponse:
    """Export a minimal account inventory for superusers only."""
    if not request.user.is_superuser:
        raise PermissionDenied

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="users.csv"'
    response["X-Content-Type-Options"] = "nosniff"
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
        ]
    )
    for user in queryset.select_related("extended_profile"):
        profile = getattr(user, "extended_profile", None)
        email_verified = getattr(user, "primary_email_verified", None)
        if email_verified is None:
            email_verified = EmailAddress.objects.filter(
                user=user,
                email__iexact=user.email,
                verified=True,
            ).exists()
        writer.writerow(
            [
                user.pk,
                _csv_safe_text(user.username),
                _csv_safe_text(user.email),
                user.is_active,
                user.is_staff,
                bool(email_verified),
                bool(profile and profile.completed_at),
            ]
        )
    return response


# allauth and session rows are implementation details. Registering them as
# normal ModelAdmin pages exposes secret-bearing fields on direct URLs and
# creates several competing ways to edit the same account. They are instead
# represented by safe summaries on the canonical auth.User page below.
for model in (
    User,
    UserProfile,
    EmailAddress,
    SocialAccount,
    SocialApp,
    SocialToken,
    Authenticator,
    UserSession,
    UserSessionMeta,
    UserSessionToken,
    OutstandingToken,
    BlacklistedToken,
    AccessAttempt,
    AccessLog,
    AccessFailureLog,
):
    _safe_unregister(model)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    actions = (export_users_csv,)
    inlines = (UserProfileInline,)
    list_display = (
        "username",
        "email",
        "is_active",
        "is_staff",
        "email_verified",
        "profile_state",
        "last_login",
    )
    list_filter = (
        "is_active",
        "is_staff",
        EmailVerifiedFilter,
        ProfileCompleteFilter,
    )
    search_fields = (
        "username",
        "email",
        "extended_profile__vk_username",
        "extended_profile__minecraft_nick",
        "extended_profile__itmo_isu",
    )
    ordering = ("-date_joined",)
    list_per_page = 50
    list_max_show_all = 200
    readonly_fields = (
        "date_joined",
        "last_login",
        "identity_summary",
        "security_summary",
    )
    fieldsets = (
        (
            "Account",
            {
                "fields": (
                    "username",
                    "password",
                    ("first_name", "last_name"),
                    "email",
                    "is_active",
                )
            },
        ),
        (
            "Identity and security",
            {"fields": ("identity_summary", "security_summary")},
        ),
        (
            "Staff access",
            {
                "classes": ("collapse",),
                "fields": (
                    ("is_staff", "is_superuser"),
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Activity",
            {
                "classes": ("collapse",),
                "fields": ("last_login", "date_joined"),
            },
        ),
    )
    add_fieldsets = (
        (
            "Create account",
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
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
        return queryset.select_related("extended_profile").annotate(
            profile_completed=Exists(
                UserProfile.objects.filter(
                    user=OuterRef("pk"),
                    completed_at__isnull=False,
                )
            ),
            primary_email_verified=Exists(verified_email),
        )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly.extend(_PRIVILEGE_FIELDS)
        return tuple(dict.fromkeys(readonly))

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None or request.user.is_superuser:
            return fieldsets

        safe_fieldsets = []
        for title, options in fieldsets:
            safe_options = options.copy()
            safe_fields = []
            for field in safe_options.get("fields", ()):
                if field == "password":
                    continue
                if isinstance(field, (list, tuple)):
                    field = tuple(item for item in field if item != "password")
                    if not field:
                        continue
                safe_fields.append(field)
            safe_options["fields"] = tuple(safe_fields)
            safe_fieldsets.append((title, safe_options))
        return tuple(safe_fieldsets)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            actions.pop("export_users_csv", None)
            actions.pop("delete_selected", None)
        return actions

    def has_change_permission(self, request, obj=None) -> bool:
        if not super().has_change_permission(request, obj):
            return False
        return bool(
            request.user.is_superuser or obj is None or not obj.is_superuser
        )

    def has_delete_permission(self, request, obj=None) -> bool:
        return bool(
            request.user.is_superuser
            and super().has_delete_permission(request, obj)
        )

    def user_change_password(self, request, id, form_url=""):
        if not request.user.is_superuser:
            raise PermissionDenied
        return super().user_change_password(request, id, form_url)

    @admin.display(boolean=True, ordering="primary_email_verified")
    def email_verified(self, obj) -> bool:
        return bool(getattr(obj, "primary_email_verified", False))

    @admin.display(description="Profile", ordering="profile_completed")
    def profile_state(self, obj) -> str:
        profile = getattr(obj, "extended_profile", None)
        if profile and profile.completed_at:
            return "complete"
        if profile:
            return "started"
        return "missing"

    @admin.display(description="Connected identity")
    def identity_summary(self, obj) -> str:
        email_is_verified = EmailAddress.objects.filter(
            user=obj,
            email__iexact=obj.email,
            verified=True,
        ).exists()
        providers = list(
            SocialAccount.objects.filter(user=obj)
            .order_by("provider")
            .values_list("provider", flat=True)
            .distinct()
        )
        return format_html(
            "<strong>Primary email:</strong> {} ({})<br>"
            "<strong>Connected providers:</strong> {}",
            obj.email or "missing",
            "verified" if email_is_verified else "not verified",
            ", ".join(providers) if providers else "none",
        )

    @admin.display(description="Security overview")
    def security_summary(self, obj) -> str:
        factor_labels = dict(Authenticator.Type.choices)
        factors = (
            Authenticator.objects.filter(user=obj)
            .order_by("type", "created_at")
            .values_list("type", "created_at", "last_used_at")
        )
        factor_summary = "; ".join(
            (
                f"{factor_labels.get(factor_type, factor_type)} — "
                f"created {_admin_datetime(created_at)}, "
                f"last used {_admin_datetime(last_used_at)}"
            )
            for factor_type, created_at, last_used_at in factors
        )
        browser_session_count = UserSession.objects.filter(user=obj).count()
        refresh_session_count = UserSessionToken.objects.filter(
            user=obj,
            revoked_at__isnull=True,
        ).count()
        return format_html(
            "<strong>MFA factors:</strong> {}<br>"
            "<strong>Tracked browser sessions:</strong> {}<br>"
            "<strong>Active refresh sessions:</strong> {}",
            factor_summary or "not configured",
            browser_session_count,
            refresh_session_count,
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        sync_user_email_address(obj)
