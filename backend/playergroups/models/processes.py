from django.conf import settings
from django.db import models


class ParticipationProcess(models.Model):
    group = models.ForeignKey(
        "playergroups.PlayerGroup", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=500, blank=True)

    class Meta:
        abstract = True


class GroupJoinRequest(ParticipationProcess):
    status = models.CharField(
        max_length=12,
        default="pending",
        choices=[
            (x, x)
            for x in (
                "pending",
                "accepted",
                "rejected",
                "cancelled",
                "expired",
            )
        ],
    )
    answer = models.CharField(max_length=1000, blank=True)
    visibility = models.CharField(max_length=12, default="private")
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolved_group_requests",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "user"],
                condition=models.Q(status="pending"),
                name="group_request_pending_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "pending",
                        "accepted",
                        "rejected",
                        "cancelled",
                        "expired",
                    ]
                ),
                name="group_request_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    visibility__in=["public", "members", "private"]
                ),
                name="group_request_visibility_valid",
            ),
        ]
        indexes = [models.Index(fields=["user", "status"])]


class GroupInvitation(ParticipationProcess):
    status = models.CharField(
        max_length=12,
        default="pending",
        choices=[
            (x, x)
            for x in ("pending", "accepted", "declined", "revoked", "expired")
        ],
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="sent_group_invitations",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "user"],
                condition=models.Q(status="pending"),
                name="group_invite_pending_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "pending",
                        "accepted",
                        "declined",
                        "revoked",
                        "expired",
                    ]
                ),
                name="group_invite_status_valid",
            ),
        ]
        indexes = [models.Index(fields=["user", "status"])]


class GroupLeadershipOffer(ParticipationProcess):
    status = models.CharField(
        max_length=12,
        default="pending",
        choices=[
            (x, x)
            for x in ("pending", "accepted", "declined", "revoked", "expired")
        ],
    )
    offered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="sent_group_leadership_offers",
    )
    transfer = models.BooleanField(default=False)
    recovery = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "user"],
                condition=models.Q(status="pending"),
                name="group_offer_pending_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "pending",
                        "accepted",
                        "declined",
                        "revoked",
                        "expired",
                    ]
                ),
                name="group_offer_status_valid",
            ),
        ]
        indexes = [models.Index(fields=["user", "status"])]
