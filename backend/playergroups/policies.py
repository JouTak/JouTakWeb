from accounts.api.errors import raise_structured_error
from communities.access import authenticated
from communities.models import CommunityMembership
from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from playergroups.models import GroupMembership, GroupRestriction


def fail(code, detail, status=409):
    raise_structured_error(status, detail=detail, error_code=f"GROUP_{code}")


def is_operator(user):
    # Do not reuse Django's per-instance permission cache across a mutation.
    return authenticated(user) and operator_users().filter(pk=user.pk).exists()


def operator_users():
    return (
        get_user_model()
        .objects.filter(is_active=True)
        .filter(
            Q(is_superuser=True)
            | Q(
                user_permissions__codename="moderate_playergroup",
                user_permissions__content_type__app_label="playergroups",
            )
            | Q(
                groups__permissions__codename="moderate_playergroup",
                groups__permissions__content_type__app_label="playergroups",
            )
        )
    )


def active_restrictions():
    return GroupRestriction.objects.filter(active=True).filter(
        Q(until__isnull=True) | Q(until__gt=timezone.now())
    )


def eligible(user, group):
    if (
        not authenticated(user)
        or not get_user_model()
        .objects.filter(pk=user.pk, is_active=True)
        .exists()
    ):
        return False
    return (
        not group.scope_id
        or CommunityMembership.objects.filter(
            user=user,
            community_id=group.scope_id,
            status="active",
            community__status="active",
        ).exists()
    )


def effective_members(group):
    query = group.memberships.filter(
        status="active", user__is_active=True
    ).exclude(
        user_id__in=active_restrictions().filter(group=group).values("user_id")
    )
    if group.scope_id:
        query = query.filter(
            user__community_memberships__community_id=group.scope_id,
            user__community_memberships__status="active",
            group__scope__status="active",
        )
    return query


def effective_memberships():
    """Effective participation, with current scope and restrictions."""
    return (
        GroupMembership.objects.filter(status="active", user__is_active=True)
        .annotate(
            scope_valid=Exists(
                CommunityMembership.objects.filter(
                    user_id=OuterRef("user_id"),
                    community_id=OuterRef("group__scope_id"),
                    status="active",
                    community__status="active",
                )
            ),
            participation_blocked=Exists(
                active_restrictions().filter(
                    user_id=OuterRef("user_id"), group_id=OuterRef("group_id")
                )
            ),
        )
        .filter(participation_blocked=False)
        .filter(Q(group__scope__isnull=True) | Q(scope_valid=True))
    )


class GroupPolicy:
    def __init__(self, user, group, *, context=None):
        self.user, self.group = user, group
        if context is not None:
            key = (user.pk if user else None, group.pk)
            self.operator = bool(user and user.pk in context.operators)
            self.eligible = context.eligible(user, group)
            self.blocked = key in context.blocked
            self.membership = context.members.get(key)
            self.role = (
                self.membership.role
                if self.membership
                and self.membership.status == "active"
                and self.eligible
                and not self.blocked
                else None
            )
            return
        self.operator = is_operator(user)
        self.eligible = eligible(user, group)
        self.blocked = bool(
            authenticated(user)
            and active_restrictions().filter(group=group, user=user).exists()
        )
        self.membership = (
            group.memberships.filter(user=user).first()
            if authenticated(user)
            else None
        )
        self.role = (
            self.membership.role
            if self.membership
            and self.membership.status == "active"
            and self.eligible
            and not self.blocked
            else None
        )

    def can_view(self):
        return (
            self.operator
            or bool(self.role)
            or (
                self.group.status == "active"
                and not self.group.restricted
                and self.group.access != "private"
            )
        )

    def can_work(self):
        return not self.group.restricted and self.group.status != "archived"

    def can_manage(self):
        return self.operator or (
            self.can_work() and self.role in {"manager", "moderator"}
        )

    def can_configure(self):
        return self.operator or (self.can_work() and self.role == "manager")

    def can_enter(self):
        return (
            self.eligible
            and not self.blocked
            and self.group.status == "active"
            and not self.group.restricted
            and self.group.accepting
        )

    def require(self, action):
        if not self.can_view():
            fail("NOT_FOUND", "Страница недоступна.", 404)
        allowed = {
            "view": True,
            "manage": self.can_manage(),
            "configure": self.can_configure(),
            "moderate": self.operator,
        }[action]
        if not allowed:
            fail(
                "PERMISSION_DENIED",
                "Ваших прав недостаточно для этого действия.",
                403,
            )

    def require_entry(self):
        if not self.eligible:
            fail(
                "SCOPE_REQUIRED",
                "Нужно действующее участие в серверном сообществе.",
                403,
            )
        if self.blocked:
            fail(
                "PARTICIPATION_RESTRICTED",
                "Участие в этом объединении ограничено.",
                403,
            )
        if not self.can_enter():
            fail("JOIN_PAUSED", "Объединение сейчас не принимает участников.")

    def require_target(self, member, *, role_change=False):
        self.require("configure" if role_change else "manage")
        if not self.operator and (
            member.role == "manager"
            or (self.role == "moderator" and member.role != "member")
        ):
            fail("ROLE_PROTECTED", "Эта роль недоступна для изменения.", 403)


def guard_last_manager(group, member, *, excluded_users=()):
    if (
        member.status != "active"
        or member.role != "manager"
        or group.status == "archived"
        or group.restricted
    ):
        return
    if (
        not effective_members(group)
        .filter(role="manager")
        .exclude(pk=member.pk)
        .exclude(user_id__in=excluded_users)
        .exists()
    ):
        fail(
            "LAST_MANAGER",
            "Сначала передайте руководство другому участнику "
            "или отправьте объединение в архив.",
        )
