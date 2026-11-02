from communities.models import CommunityMembership
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver

from cities.membership_service import (
    guard_account_deletion,
    guard_last_manager,
)
from cities.models import City, CityMembership


@receiver(pre_delete, sender=settings.AUTH_USER_MODEL)
def protect_account_governance(sender, instance, origin=None, **kwargs):
    removed = (
        origin.values_list("pk", flat=True)
        if isinstance(origin, QuerySet)
        else ()
    )
    guard_account_deletion(instance, removed_users=removed)


@receiver(pre_save, sender=CommunityMembership)
def protect_community_membership(sender, instance, **kwargs):
    if instance.status == "active" or not instance.pk:
        return
    for city in (
        City.objects.select_for_update(of=("self",))
        .filter(
            community_id=instance.community_id,
            memberships__user_id=instance.user_id,
            memberships__role="manager",
            memberships__status="active",
        )
        .order_by("pk")
    ):
        guard_last_manager(
            city, city.memberships.get(user_id=instance.user_id)
        )


def is_user_deletion(origin):
    return isinstance(origin, get_user_model()) or (
        isinstance(origin, QuerySet) and origin.model is get_user_model()
    )


@receiver(pre_delete, sender=CommunityMembership)
def protect_community_membership_delete(
    sender, instance, origin=None, **kwargs
):
    if is_user_deletion(origin):
        return
    removed = (
        origin.filter(community_id=instance.community_id).values_list(
            "user_id", flat=True
        )
        if isinstance(origin, QuerySet)
        else ()
    )
    for city in (
        City.objects.select_for_update(of=("self",))
        .filter(
            community_id=instance.community_id,
            memberships__user_id=instance.user_id,
            memberships__role="manager",
            memberships__status="active",
        )
        .order_by("pk")
    ):
        guard_last_manager(
            city,
            city.memberships.get(user_id=instance.user_id),
            removed_users=removed,
        )


@receiver(pre_delete, sender=CityMembership)
def protect_membership_delete(sender, instance, origin=None, **kwargs):
    # Account deletion is guarded once by the User pre_delete receiver.
    if is_user_deletion(origin):
        return
    city = City.objects.select_for_update(of=("self",)).get(
        pk=instance.city_id
    )
    removed = (
        origin.values_list("pk", flat=True)
        if isinstance(origin, QuerySet)
        else ()
    )
    guard_last_manager(city, instance, removed_members=removed)
