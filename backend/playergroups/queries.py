from communities.access import authenticated
from communities.models import CommunityMembership
from django.db.models import Exists, OuterRef, Q

from playergroups.common import find_group
from playergroups.models import (
    GroupInvitation,
    GroupJoinRequest,
    GroupLeadershipOffer,
    GroupMembership,
    PlayerGroup,
)
from playergroups.policies import GroupPolicy, active_restrictions, is_operator
from playergroups.process_state import PROCESS_MODELS, process_status
from playergroups.read_context import GroupReadContext
from playergroups.schemas import (
    Capabilities,
    ContactIn,
    GroupCardOut,
    GroupListOut,
    GroupOut,
    ViewerOut,
)
from playergroups.serializers import group_ref, membership_out, process_out


def visible_groups(viewer, *, catalog=False):
    public = Q(
        status="active",
        restricted=False,
        access="public" if catalog else "public",
    )
    if not catalog:
        public |= Q(status="active", restricted=False, access="unlisted")
    query = PlayerGroup.objects.select_related("scope")
    if authenticated(viewer):
        member = GroupMembership.objects.filter(
            group_id=OuterRef("pk"), user=viewer, status="active"
        )
        scope_member = CommunityMembership.objects.filter(
            community_id=OuterRef("scope_id"),
            user=viewer,
            status="active",
            community__status="active",
        )
        blocked = active_restrictions().filter(
            group_id=OuterRef("pk"), user=viewer
        )
        query = query.annotate(
            own=Exists(member),
            in_scope=Exists(scope_member),
            blocked=Exists(blocked),
        )
        access = Q(own=True, blocked=False) & (
            Q(scope__isnull=True) | Q(in_scope=True)
        )
        # Unlisted/private memberships belong in the account, never discovery.
        if not catalog:
            public |= access
    return query.filter(public)


def catalog(viewer, filters, flags):
    query = visible_groups(viewer, catalog=True)
    if filters.q:
        query = query.filter(
            Q(name__icontains=filters.q)
            | Q(short_description__icontains=filters.q)
        )
    if filters.scope:
        query = query.filter(scope__slug=filters.scope)
    if filters.join_mode:
        query = query.filter(join_mode=filters.join_mode)
    if filters.category:
        query = query.filter(category=filters.category)
    total = query.count()
    groups = list(
        query.order_by("name", "pk")[
            (filters.page - 1) * 24 : filters.page * 24
        ]
    )
    own = {}
    if authenticated(viewer):
        own = {
            m.group_id: m
            for m in GroupMembership.objects.filter(
                group__in=groups, user=viewer
            ).select_related("group", "group__scope", "user")
        }
    items = []
    pending = {}
    if authenticated(viewer):
        for kind in ("request", "invitation", "leadership"):
            processes = list(
                process_queryset(None, kind).filter(
                    group__in=groups, user=viewer, status="pending"
                )
            )
            context = GroupReadContext.for_processes(processes, viewer)
            for process in processes:
                if process_status(process, context=context) == "pending":
                    pending[process.group_id] = kind
    # One scope lookup per page, regardless of membership count.
    scopes = (
        set(
            viewer.community_memberships.filter(
                status="active", community__status="active"
            ).values_list("community_id", flat=True)
        )
        if authenticated(viewer)
        else set()
    )
    for group in groups:
        member = own.get(group.pk)
        items.append(
            GroupCardOut(
                **group_ref(group).model_dump(),
                membership=membership_out(
                    member,
                    is_eligible=not group.scope_id or group.scope_id in scopes,
                )
                if member
                else None,
                pending=pending.get(group.pk),
            )
        )
    return GroupListOut(
        items=items,
        total=total,
        page=filters.page,
        can_create=bool(
            authenticated(viewer) and flags.get("player_groups_write")
        ),
        can_moderate=is_operator(viewer),
    )


def viewer_process(group, viewer, model, kind):
    if not authenticated(viewer):
        return None
    process = (
        model.objects.filter(group=group, user=viewer)
        .select_related("user__community_profile", "user__extended_profile")
        .order_by("-created_at", "-pk")
        .first()
    )
    return process_out(process, viewer, kind) if process else None


def detail(viewer, slug, flags):
    group = find_group(slug)
    policy = GroupPolicy(viewer, group)
    policy.require("view")
    write = bool(flags.get("player_groups_write"))
    state = (
        "guest"
        if not authenticated(viewer)
        else "restricted"
        if policy.blocked
        else "scope_required"
        if not policy.eligible
        else "member"
        if policy.role
        else "eligible"
    )
    membership = (
        membership_out(policy.membership, is_eligible=policy.eligible)
        if policy.membership
        else None
    )
    contacts = group.contacts.all()
    if not policy.role and not policy.operator:
        contacts = contacts.filter(visibility="public")
    return GroupOut(
        **group_ref(group).model_dump(),
        description=group.description,
        rules=group.rules,
        welcome=group.welcome if policy.role or policy.operator else "",
        application_question=group.application_question,
        cover_url=group.cover_url,
        contacts=[
            ContactIn.model_validate(c, from_attributes=True) for c in contacts
        ],
        roster_visibility=group.roster_visibility,
        version=group.version,
        updated_at=group.updated_at,
        viewer=ViewerOut(
            state=state,
            membership=membership,
            invitation=viewer_process(
                group, viewer, GroupInvitation, "invitation"
            ),
            request=viewer_process(group, viewer, GroupJoinRequest, "request"),
            leadership=viewer_process(
                group, viewer, GroupLeadershipOffer, "leadership"
            ),
        ),
        capabilities=Capabilities(
            write_enabled=write,
            join=write
            and policy.can_enter()
            and not policy.role
            and group.join_mode == "open",
            apply=write
            and policy.can_enter()
            and not policy.role
            and group.join_mode == "approval",
            edit=write and policy.can_manage() and group.status != "archived",
            manage=policy.can_manage(),
            configure=write
            and (
                policy.can_configure()
                or (policy.role == "manager" and not group.restricted)
            ),
            moderate=policy.operator,
            leave=write
            and bool(
                policy.membership and policy.membership.status == "active"
            ),
            respond=write and policy.can_enter(),
        ),
    )


def process_queryset(group, kind):
    model = PROCESS_MODELS[kind]
    related = [
        "group__scope",
        "user__community_profile",
        "user__extended_profile",
    ]
    sender = (
        "invited_by"
        if kind == "invitation"
        else "offered_by"
        if kind == "leadership"
        else None
    )
    if sender:
        related.extend(
            [f"{sender}__community_profile", f"{sender}__extended_profile"]
        )
    query = model.objects.select_related(*related).order_by(
        "-created_at", "-pk"
    )
    return query.filter(group=group) if group else query
