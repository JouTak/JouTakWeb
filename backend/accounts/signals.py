from __future__ import annotations

from accounts.services.email_addresses import sync_user_email_address
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


@receiver(user_logged_in)
def ensure_email_address_synced(sender, request, user, **kwargs) -> None:
    sync_user_email_address(user)
