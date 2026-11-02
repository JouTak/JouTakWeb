from django.contrib.auth import get_user_model
from django.db import transaction

from profiles.contact_schemas import (
    ContactInput,
    SelfContactsOut,
    contact_url,
    normalize_contact,
)
from profiles.editing import check_version, locked_profile
from profiles.models import CommunityProfile, ProfileContact
from profiles.policy import visible
from profiles.schemas import ProfileContactOut


def effective_contacts(subject):
    contacts = list(subject.profile_contacts.all())
    profile = getattr(subject, "community_profile", None)
    legacy = getattr(subject, "extended_profile", None)
    if (
        profile
        and profile.legacy_vk_enabled
        and legacy
        and legacy.vk_username
        and not any(c.type == "vk" for c in contacts)
    ):
        try:
            contacts.append(
                ContactInput(
                    type="vk",
                    value=normalize_contact("vk", legacy.vk_username),
                    visibility=profile.social_visibility,
                )
            )
        except ValueError:
            # An invalid old account identifier is not a publishable URL.
            pass
    return contacts


def public_contacts(subject, *, own=False, shared=False):
    return [
        ProfileContactOut(
            type=c.type, value=c.value, url=contact_url(c.type, c.value)
        )
        for c in effective_contacts(subject)
        if visible(c.visibility, own=own, shared=shared)
    ]


def self_contacts(actor):
    profile = getattr(actor, "community_profile", None) or CommunityProfile(
        user=actor
    )
    return SelfContactsOut(
        version=profile.contacts_version,
        contacts=[
            {"type": c.type, "value": c.value, "visibility": c.visibility}
            for c in effective_contacts(actor)
        ],
    )


@transaction.atomic
def save_contacts(actor, payload):
    actor = get_user_model().objects.select_for_update().get(pk=actor.pk)
    profile = locked_profile(actor)
    check_version(profile.contacts_version, payload.version)
    ProfileContact.objects.filter(user=actor).delete()
    ProfileContact.objects.bulk_create(
        [
            ProfileContact(user=actor, **item.model_dump())
            for item in payload.contacts
        ]
    )
    profile.legacy_vk_enabled = False
    profile.contacts_version += 1
    profile.save(
        update_fields=["legacy_vk_enabled", "contacts_version", "updated_at"]
    )
    actor.community_profile = profile
    return self_contacts(actor)
