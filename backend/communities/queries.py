from accounts.api.errors import raise_structured_error
from cities.models import City
from django.db.models import Count, Exists, OuterRef, Q
from profiles.schemas import CommunityMembershipOut

from communities.access import authenticated
from communities.models import Community
from communities.schemas import CommunityOut


def visible_communities(user):
    visibility = Q(visibility="public")
    if authenticated(user):
        visibility |= Q(memberships__user=user, memberships__status="active")
    return (
        Community.objects.filter(status="active").filter(visibility).distinct()
    )


def community_queryset(user):
    return Community.objects.filter(pk__in=visible_communities(user)).annotate(
        member_count=Count(
            "memberships", filter=Q(memberships__status="active")
        ),
        has_cities=Exists(
            City.objects.filter(community_id=OuterRef("pk"), status="active")
        ),
    )


def community_out(community):
    return CommunityOut.model_validate(community, from_attributes=True)


def community_detail(user, slug):
    community = community_queryset(user).filter(slug=slug).first()
    if not community:
        raise_structured_error(
            404,
            detail="Сообщество не найдено.",
            error_code="COMMUNITY_NOT_FOUND",
        )
    result = community_out(community)
    if authenticated(user):
        membership = community.memberships.filter(user=user).first()
        if membership:
            result.membership = CommunityMembershipOut(
                community={"slug": community.slug, "name": community.name},
                role=membership.role,
                status=membership.status,
                joined_at=membership.joined_at,
            )
    return result
