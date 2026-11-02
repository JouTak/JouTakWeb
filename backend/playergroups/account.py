from django.db.models import CharField, Q, Value
from profiles.connections import accessible_players
from profiles.policy import shared_communities, visible

from playergroups.models import (
    GroupInvitation,
    GroupJoinRequest,
    GroupLeadershipOffer,
    GroupMembership,
)
from playergroups.policies import (
    GroupPolicy,
    effective_memberships,
    fail,
)
from playergroups.queries import visible_groups
from playergroups.read_context import GroupReadContext
from playergroups.schemas import (
    AccountGroupListOut,
    AccountGroupOut,
    AccountProcessListOut,
    AccountProcessOut,
    GroupCardOut,
    GroupListOut,
)
from playergroups.serializers import group_ref, membership_out, process_out


def account_groups(actor, page, history):
    query = (
        GroupMembership.objects.filter(user=actor)
        .select_related("group__scope", "user")
        .order_by("group__name", "pk")
    )
    if history:
        query = query.exclude(
            status="active", group__status__in=["draft", "active"]
        )
    else:
        query = query.filter(
            status="active", group__status__in=["draft", "active"]
        )
    rows = list(query[(page - 1) * 24 : page * 24])
    context = GroupReadContext([m.group for m in rows], [actor], actor)
    return AccountGroupListOut(
        items=[
            AccountGroupOut(
                group=(
                    group_ref(m.group)
                    if GroupPolicy(actor, m.group, context=context).can_view()
                    else None
                ),
                membership=membership_out(
                    m, is_eligible=context.eligible(actor, m.group)
                ),
            )
            for m in rows
        ],
        total=query.count(),
        page=page,
    )


def own_processes(actor, page, flags):
    models = {
        "invitation": GroupInvitation,
        "request": GroupJoinRequest,
        "leadership": GroupLeadershipOffer,
    }
    parts = [
        model.objects.filter(user=actor)
        .annotate(kind=Value(kind, output_field=CharField()))
        .values("id", "created_at", "kind")
        for kind, model in models.items()
    ]
    query = parts[0].union(*parts[1:]).order_by("-created_at", "kind", "id")
    rows = list(query[(page - 1) * 24 : page * 24])
    found = {}
    for kind, model in models.items():
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
            related += [
                f"{sender}__community_profile",
                f"{sender}__extended_profile",
            ]
        for process in model.objects.filter(
            pk__in=[r["id"] for r in rows if r["kind"] == kind]
        ).select_related(*related):
            found[(kind, process.pk)] = process
    context = GroupReadContext.for_processes(found.values(), actor)
    items = []
    for row in rows:
        process = found[(row["kind"], row["id"])]
        out = process_out(process, actor, row["kind"], context=context)
        allowed = GroupPolicy(
            actor, process.group, context=context
        ).can_view() or (
            row["kind"] in {"invitation", "leadership"}
            and out.status == "pending"
        )
        items.append(
            AccountProcessOut(
                process=out,
                group=group_ref(process.group) if allowed else None,
                rules=process.group.rules if allowed else "",
            )
        )
    return AccountProcessListOut(
        items=items,
        total=query.count(),
        page=page,
        write_enabled=bool(flags.get("player_groups_write")),
    )


def profile_groups(viewer, username, page):
    # Group membership never extends the old 'community' audience.
    own = bool(viewer and viewer.username == username)
    if own:
        subject = viewer
    else:
        subject = accessible_players(viewer).filter(username=username).first()
    if not subject:
        fail("PROFILE_NOT_FOUND", "Профиль недоступен.", 404)
    profile = getattr(subject, "community_profile", None)
    allowed = bool(
        profile
        and visible(
            profile.memberships_visibility,
            own=own,
            shared=shared_communities(viewer, subject),
        )
    )
    if not allowed:
        return GroupListOut(items=[], total=0, page=page)
    query = effective_memberships().filter(
        user=subject,
        status="active",
        group__in=visible_groups(viewer),
        group__status="active",
    )
    if not own:
        viewer_groups = (
            effective_memberships().filter(user=viewer).values("group_id")
            if viewer
            else []
        )
        query = query.filter(
            Q(visibility="public")
            | Q(visibility="members", group_id__in=viewer_groups)
        )
        query = query.filter(
            Q(group__access="public") | Q(group_id__in=viewer_groups)
        )
    query = query.select_related("group__scope").order_by("group__name", "pk")
    return GroupListOut(
        items=[
            GroupCardOut(**group_ref(m.group).model_dump())
            for m in query[(page - 1) * 24 : page * 24]
        ],
        total=query.count(),
        page=page,
    )
