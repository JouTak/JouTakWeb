from profiles.policy import identity

from playergroups.policies import GroupPolicy, eligible
from playergroups.process_state import process_status
from playergroups.schemas import GroupRef, MembershipOut, ProcessOut


def group_ref(group):
    return GroupRef(
        slug=group.slug,
        name=group.name,
        short_description=group.short_description,
        logo_url=group.logo_url,
        category=group.category,
        scope={"slug": group.scope.slug, "name": group.scope.name}
        if group.scope and group.scope.visibility == "public"
        else None,
        status=group.status,
        access=group.access,
        join_mode=group.join_mode,
        accepting=group.accepting,
        restricted=group.restricted,
    )


def membership_out(member, *, is_eligible=None):
    return MembershipOut(
        id=member.pk,
        role=member.role,
        status=member.status,
        visibility=member.visibility,
        joined_at=member.joined_at,
        eligible=eligible(member.user, member.group)
        if is_eligible is None
        else is_eligible,
    )


def process_out(process, viewer, kind, *, context=None):
    person = identity(
        process.user,
        viewer,
        shared=process.user_id in context.shared_users if context else None,
    )
    sender = getattr(process, "invited_by", None) or getattr(
        process, "offered_by", None
    )
    sender_person = (
        identity(
            sender,
            viewer,
            shared=sender.pk in context.shared_users if context else None,
        )
        if sender
        else {}
    )
    own = process.user_id == viewer.pk
    management = (
        not own
        and GroupPolicy(viewer, process.group, context=context).can_manage()
    )
    return ProcessOut(
        id=process.pk,
        kind=kind,
        status=process_status(process, context=context),
        created_at=process.created_at,
        expires_at=process.expires_at,
        reason=process.reason,
        answer=getattr(process, "answer", "") if own or management else "",
        username=process.user.username
        if own or management
        else person.get("username"),
        minecraft_nick=person.get("minecraft_nick"),
        sender_username=sender_person.get("username"),
        sender_nick=sender_person.get("minecraft_nick"),
        transfer=getattr(process, "transfer", False),
        recovery=getattr(process, "recovery", False),
    )
