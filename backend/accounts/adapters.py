from __future__ import annotations

import ipaddress
from datetime import timedelta

from accounts.services.email_delivery import (
    ACTIVE_STATUSES,
    is_delivering_now,
)
from allauth.account import app_settings as allauth_settings
from allauth.account.adapter import DefaultAccountAdapter
from core.models import EmailVerificationTask
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.db import transaction
from django.utils import timezone
from django_q.tasks import async_task

UNKNOWN_IP = "0.0.0.0"
Network = ipaddress.IPv4Network | ipaddress.IPv6Network


class StrictAccountAdapter(DefaultAccountAdapter):
    def _parse_ip(self, value: str | None) -> str | None:
        raw = (value or "").strip()
        if not raw:
            return None
        try:
            return str(ipaddress.ip_address(raw))
        except ValueError:
            return None

    def _trusted_proxy_networks(self) -> tuple[Network, ...]:
        networks: list[Network] = []
        for raw in getattr(settings, "ACCOUNT_TRUSTED_PROXY_CIDRS", ()):
            try:
                networks.append(ipaddress.ip_network(raw, strict=False))
            except ValueError:
                continue
        return tuple(networks)

    def _ip_in_networks(
        self,
        value: str | None,
        networks: tuple[Network, ...],
    ) -> bool:
        if not value or not networks:
            return False
        try:
            candidate = ipaddress.ip_address(value)
        except ValueError:
            return False
        return any(candidate in network for network in networks)

    def _remote_is_trusted_proxy(self, remote_ip: str | None) -> bool:
        if not remote_ip:
            return False
        if not getattr(settings, "ACCOUNT_TRUST_PROXY_HEADERS", False):
            return False
        try:
            remote_addr = ipaddress.ip_address(remote_ip)
        except ValueError:
            return False
        networks = self._trusted_proxy_networks()
        if networks:
            return any(remote_addr in network for network in networks)
        return False

    def _forwarded_client_ip(
        self,
        request,
        *,
        trusted_networks: tuple[Network, ...],
    ) -> str | None:
        real_ip = self._parse_ip(request.META.get("HTTP_X_REAL_IP"))
        if real_ip:
            return real_ip

        raw_value = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if not raw_value:
            return None

        parsed_chain = [
            parsed
            for part in raw_value.split(",")
            for parsed in [self._parse_ip(part)]
            if parsed
        ]
        if not parsed_chain:
            return None

        for candidate in reversed(parsed_chain):
            if not self._ip_in_networks(candidate, trusted_networks):
                return candidate
        return None

    def get_client_ip(self, request) -> str:
        remote_ip = self._parse_ip(request.META.get("REMOTE_ADDR"))
        trusted_networks = self._trusted_proxy_networks()
        if self._remote_is_trusted_proxy(remote_ip):
            forwarded_ip = self._forwarded_client_ip(
                request,
                trusted_networks=trusted_networks,
            )
            if forwarded_ip:
                return forwarded_ip
        return remote_ip or UNKNOWN_IP

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        if is_delivering_now() or (
            allauth_settings.EMAIL_VERIFICATION_BY_CODE_ENABLED
        ):
            # The worker is sending now. A one-time code cannot be
            # regenerated later, so the code flow keeps the plain path.
            super().send_confirmation_mail(request, emailconfirmation, signup)
            return
        address = emailconfirmation.email_address
        kinds = EmailVerificationTask.Kind
        kind = (
            kinds.EMAIL_CONFIRMATION_SIGNUP
            if signup
            else kinds.EMAIL_CONFIRMATION
        )
        self._enqueue_tracked(kind, address.user, address.email)

    def send_password_reset_mail(self, user, email, context):
        if is_delivering_now():
            super().send_password_reset_mail(user, email, context)
            return
        self._enqueue_tracked(
            EmailVerificationTask.Kind.PASSWORD_RESET, user, email
        )

    def send_mail(self, template_prefix, email, context):
        # Guard: allauth may omit the current site, templates need it.
        if context.get("current_site") is None:
            context["current_site"] = Site.objects.get_current()
        if "site" not in context:
            context["site"] = context["current_site"]

        if is_delivering_now():
            super().send_mail(template_prefix, email, context)
            return

        # Mails without secrets (e.g. unknown account notices) are
        # rendered now and queued as is, never sent from the request.
        msg = self.render_mail(template_prefix, email, context)
        async_task(
            "accounts.tasks.send_plain_email_task",
            to=list(msg.to),
            subject=msg.subject,
            body=msg.body,
            from_email=msg.from_email,
            subtype=msg.content_subtype,
            alternatives=[(a[0], a[1]) for a in msg.alternatives],
        )

    def _enqueue_tracked(self, kind, user, email):
        """Queue a mail whose secrets are generated by the worker.

        Only the tracker id goes into the queue: confirmation keys and
        reset tokens never reach the task payload, and they are created
        when the message is actually sent, so they are always fresh.

        One mail per address and purpose: a request while the mail is
        still queued or inside the cooldown changes nothing. The two
        confirmation kinds (signup and manual) count as one purpose.
        """
        confirmation_kinds = EmailVerificationTask.CONFIRMATION_KINDS
        purpose = confirmation_kinds if kind in confirmation_kinds else (kind,)
        now = timezone.now()
        cooldown = timedelta(seconds=settings.EMAIL_RESEND_COOLDOWN_SECONDS)

        # The queue lives in the same database, so the tracker and its
        # task are committed together (or not at all).
        with transaction.atomic():
            # Serializes concurrent requests of one user (a row lock on
            # PostgreSQL): two parallel requests cannot both queue a mail.
            get_user_model().objects.select_for_update().filter(
                pk=user.pk
            ).first()
            tracker = (
                EmailVerificationTask.objects.filter(
                    email=email, kind__in=purpose
                )
                .order_by("-updated_at", "-id")
                .first()
            )
            if tracker is not None and (
                tracker.status in ACTIVE_STATUSES
                or (tracker.next_allowed_at and tracker.next_allowed_at > now)
            ):
                return
            if tracker is None:
                tracker = EmailVerificationTask(email=email)
            tracker.user = user
            tracker.kind = kind
            tracker.status = EmailVerificationTask.Status.WAITING
            tracker.attempts = 0
            tracker.last_error = ""
            tracker.next_attempt_at = None
            tracker.locked_until = None
            tracker.next_allowed_at = now + cooldown
            tracker.save()
            tracker.task_id = async_task(
                "accounts.tasks.send_email_task", tracker_id=tracker.id
            )
            tracker.save(update_fields=["task_id"])
