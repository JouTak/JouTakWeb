from __future__ import annotations

from dataclasses import dataclass

from allauth.account.models import EmailAddress
from allauth.account.utils import user_email


@dataclass(slots=True)
class EmailAddressSyncResult:
    created: bool = False
    updated_user_email: bool = False
    promoted_primary: bool = False


def sync_user_email_address(user) -> EmailAddressSyncResult:
    result = EmailAddressSyncResult()
    primary = EmailAddress.objects.get_primary(user)
    current_email = user_email(user)

    if not current_email:
        if primary and primary.email:
            user_email(user, primary.email, commit=True)
            result.updated_user_email = True
        return result

    try:
        email_address = EmailAddress.objects.get_for_user(user, current_email)
    except EmailAddress.DoesNotExist:
        email_address = EmailAddress.objects.add_email(
            request=None,
            user=user,
            email=current_email,
            confirm=False,
        )
        result.created = True

    if not email_address.primary:
        email_address.set_as_primary(conditional=False)
        result.promoted_primary = True

    normalized_email = email_address.email
    if user_email(user) != normalized_email:
        user_email(user, normalized_email, commit=True)
        result.updated_user_email = True

    return result
