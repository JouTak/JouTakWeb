import logging

from accounts.api.errors import raise_structured_error
from communities.access import authenticated

from cities.models import City, CityMembership

logger = logging.getLogger(__name__)


def is_moderator(user):
    return authenticated(user) and user.has_perm("cities.moderate_city")


class CityPolicy:
    def __init__(self, user, city):
        self.user = user
        self.city = city
        self.moderator = is_moderator(user)
        self.role = None
        if authenticated(user) and city.community.status == "active":
            self.role = (
                CityMembership.objects.filter(
                    city=city,
                    user=user,
                    status="active",
                    user__community_memberships__community_id=city.community_id,
                    user__community_memberships__status="active",
                )
                .values_list("role", flat=True)
                .first()
            )

    def can_edit(self):
        return self.moderator or (
            self.city.status != City.Status.ARCHIVED
            and self.role in {"representative", "manager"}
        )

    def can_manage_members(self):
        return self.moderator or (
            self.city.status != City.Status.ARCHIVED and self.role == "manager"
        )

    def can_view(self):
        return (
            self.moderator
            or self.can_edit()
            or (
                self.city.status == "active"
                and self.city.community.status == "active"
                and (
                    self.city.community.visibility == "public"
                    or (
                        authenticated(self.user)
                        and self.user.community_memberships.filter(
                            community_id=self.city.community_id,
                            status="active",
                        ).exists()
                    )
                )
            )
        )

    def require(self, capability):
        allowed = {
            "view": self.can_view(),
            "edit": self.can_edit(),
            "members": self.can_manage_members(),
            "moderate": self.moderator,
        }[capability]
        if not allowed:
            logger.info(
                "city_id=%s city_slug=%s actor_id=%s action=%s result=denied",
                self.city.pk,
                self.city.slug,
                getattr(self.user, "pk", None),
                capability,
            )
            raise_structured_error(
                404 if capability == "view" else 403,
                detail="Город недоступен."
                if capability == "view"
                else "Недостаточно прав.",
                error_code="CITY_NOT_FOUND"
                if capability == "view"
                else "CITY_PERMISSION_DENIED",
            )
