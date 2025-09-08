from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Optional

from django.utils import timezone
from django.contrib.sessions.models import Session
from django.contrib.auth import logout as dj_logout, get_user_model
from ninja.errors import HttpError

from allauth.usersessions.models import UserSession

from ninja_jwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from core.models import UserSessionMeta, UserSessionToken
from accounts.transport.schemas import SessionRowOut, RevokeSessionsIn

User = get_user_model()


FORWARD_HEADERS = ("HTTP_X_REAL_IP", "HTTP_X_FORWARDED_FOR")


@dataclass(slots=True)
class SessionService:
    @staticmethod
    def _client_ip(request) -> Optional[str]:
        for h in FORWARD_HEADERS:
            v = request.META.get(h)
            if v:
                return v.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    @staticmethod
    def _ua(request) -> str:
        return (request.META.get("HTTP_USER_AGENT", "") or "")[:512]

    @staticmethod
    def _header_token(request) -> str:
        return request.headers.get("X-Session-Token") or ""

    @staticmethod
    def _session_key(request) -> str:
        return request.session.session_key or ""

    @staticmethod
    def assert_session_allowed(request) -> None:
        token = SessionService._header_token(request)
        if token:
            meta = UserSessionMeta.objects.filter(session_token=token).first()
            if meta and meta.revoked_at:
                raise HttpError(401, "session revoked")
        s_key = SessionService._session_key(request)
        if s_key:
            meta = UserSessionMeta.objects.filter(session_key=s_key).first()
            if meta and meta.revoked_at:
                raise HttpError(401, "session revoked")

    @staticmethod
    def touch(request, user: User, *, throttle_seconds: int = 15) -> None:
        token = SessionService._header_token(request)
        dj_key = SessionService._session_key(request)
        if not (token or dj_key) or not getattr(
            user, "is_authenticated", False
        ):
            return

        key_for_meta = dj_key or token
        meta, _ = UserSessionMeta.objects.select_for_update().get_or_create(
            user=user,
            session_key=key_for_meta,
            defaults={"session_token": token or None},
        )
        if token and not meta.session_token:
            meta.session_token = token

        now = timezone.now()
        if (
            not meta.last_seen
            or (now - meta.last_seen).total_seconds() >= throttle_seconds
        ):
            meta.last_seen = now
            if not meta.user_agent:
                meta.user_agent = SessionService._ua(request)
            if not meta.ip:
                meta.ip = SessionService._client_ip(request)
            meta.save(
                update_fields=[
                    "last_seen",
                    "user_agent",
                    "ip",
                    "session_token",
                ]
            )

        if dj_key:
            us, created = UserSession.objects.get_or_create(
                user=user, session_key=dj_key
            )
            changed = False
            for field, value in (("last_seen", now), ("updated_at", now)):
                if hasattr(us, field):
                    setattr(us, field, value)
                    changed = True
            if created:
                for field, value in (("started_at", now), ("created", now)):
                    if hasattr(us, field):
                        setattr(us, field, value)
                        changed = True
            if not getattr(us, "user_agent", None) and hasattr(
                us, "user_agent"
            ):
                us.user_agent = meta.user_agent
                changed = True
            if hasattr(us, "ip") and not getattr(us, "ip", None):
                us.ip = meta.ip
                changed = True
            elif hasattr(us, "ip_address") and not getattr(
                us, "ip_address", None
            ):
                us.ip_address = meta.ip
                changed = True
            if changed:
                us.save()

    @staticmethod
    def _compose_row(
        request, us: Optional[UserSession], meta: Optional[UserSessionMeta]
    ) -> SessionRowOut:
        s_key = getattr(us, "session_key", None) or getattr(
            meta, "session_key", None
        )
        expires = None
        session_alive = False
        if s_key:
            try:
                s = Session.objects.get(session_key=s_key)
                expires = s.expire_date
                session_alive = True
            except Session.DoesNotExist:
                session_alive = False

        created = (
            (getattr(us, "created", None) if us else None)
            or (getattr(us, "started_at", None) if us else None)
            or (getattr(us, "login_time", None) if us else None)
            or (meta.first_seen if meta else None)
        )
        last_seen = (
            (getattr(us, "last_seen", None) if us else None)
            or (getattr(us, "updated_at", None) if us else None)
            or (meta.last_seen if meta else None)
            or created
        )
        revoked_at = (
            (getattr(us, "ended_at", None) if us else None)
            or (getattr(us, "revoked_at", None) if us else None)
            or (meta.revoked_at if meta else None)
        )
        revoked_reason = (
            (getattr(us, "ended_reason", None) if us else None)
            or (getattr(us, "revoked_reason", None) if us else None)
            or (meta.revoked_reason if meta else None)
        )

        token = SessionService._header_token(request)
        is_current = (s_key == SessionService._session_key(request)) or (
            meta and token and meta.session_token == token
        )
        is_revoked = bool(revoked_at) or not session_alive

        return SessionRowOut(
            id=s_key,
            user_agent=(getattr(us, "user_agent", None) if us else None)
            or (meta.user_agent if meta else None),
            ip=(
                (getattr(us, "ip", None) if us else None)
                or (getattr(us, "ip_address", None) if us else None)
                or (meta.ip if meta else None)
            ),
            created=created,
            last_seen=last_seen,
            expires=expires,
            current=bool(is_current),
            revoked=is_revoked,
            revoked_reason=revoked_reason,
            revoked_at=revoked_at,
        )

    @staticmethod
    def _merge_rows(
        request,
        us_list: Iterable[UserSession],
        meta_list: Iterable[UserSessionMeta],
    ) -> list[SessionRowOut]:
        by_key_us = {
            u.session_key: u
            for u in us_list
            if getattr(u, "session_key", None)
        }
        by_key_meta = {
            m.session_key: m
            for m in meta_list
            if getattr(m, "session_key", None)
        }
        all_keys = set(by_key_us) | set(by_key_meta)
        return [
            SessionService._compose_row(
                request, by_key_us.get(k), by_key_meta.get(k)
            )
            for k in sorted(all_keys)
        ]

    @staticmethod
    def list(request, user: User) -> list[SessionRowOut]:
        us_rows = list(UserSession.objects.filter(user=user))
        meta_rows = list(UserSessionMeta.objects.filter(user=user))
        return SessionService._merge_rows(request, us_rows, meta_rows)

    @staticmethod
    def _blacklist_session_tokens(user: User, session_key: str, when) -> None:
        maps = list(
            UserSessionToken.objects.filter(
                user=user, session_key=session_key, revoked_at__isnull=True
            )
        )
        for m in maps:
            ot = OutstandingToken.objects.filter(
                user=user, jti=m.refresh_jti
            ).first()
            if ot and not BlacklistedToken.objects.filter(token=ot).exists():
                BlacklistedToken.objects.get_or_create(token=ot)
            m.revoked_at = when
            m.save(update_fields=["revoked_at"])

    @staticmethod
    def _kill_django_session(request, session_key: str) -> None:
        Session.objects.filter(session_key=session_key).delete()
        if SessionService._session_key(request) == session_key:
            dj_logout(request)

    @staticmethod
    def revoke_bulk(request, payload: RevokeSessionsIn) -> dict:
        SessionService.assert_session_allowed(request)
        user: User = request.auth
        SessionService.touch(request, user)

        token = SessionService._header_token(request)
        cur_meta = UserSessionMeta.objects.filter(
            user=user, session_token=token
        ).first()
        cur_key = SessionService._session_key(request) or (
            cur_meta.session_key if cur_meta else ""
        )

        reason = (payload.reason or "bulk_except_current").lower()
        qs = UserSession.objects.filter(user=user)
        if payload.ids:
            qs = qs.filter(session_key__in=payload.ids)
        elif cur_key and payload.all_except_current:
            qs = qs.exclude(session_key=cur_key)

        now = timezone.now()
        revoked_ids, skipped_ids = [], []

        for us in qs:
            if getattr(us, "ended_at", None) or getattr(
                us, "revoked_at", None
            ):
                skipped_ids.append(us.session_key)
                continue

            for field, value in (("ended_at", now), ("revoked_at", now)):
                if hasattr(us, field):
                    setattr(us, field, value)
            for field, value in (
                ("ended_reason", reason),
                ("revoked_reason", reason),
            ):
                if hasattr(us, field):
                    setattr(us, field, value)
            if hasattr(us, "ended"):
                us.ended = True
            us.save()

            UserSessionMeta.objects.update_or_create(
                user=user,
                session_key=us.session_key,
                defaults={"revoked_at": now, "revoked_reason": reason},
            )

            SessionService._blacklist_session_tokens(user, us.session_key, now)
            SessionService._kill_django_session(request, us.session_key)

            revoked_ids.append(us.session_key)

        return {
            "ok": True,
            "reason": reason,
            "current": cur_key,
            "revoked_ids": revoked_ids,
            "skipped_ids": skipped_ids,
            "count": len(revoked_ids),
        }

    @staticmethod
    def revoke_single(
        request, *, sid: str, reason: Optional[str] = None
    ) -> dict:
        SessionService.assert_session_allowed(request)
        user: User = request.auth
        SessionService.touch(request, user)
        reason = (reason or "manual").lower()

        us = UserSession.objects.filter(user=user, session_key=sid).first()
        if not us:
            raise HttpError(404, "session not found")

        now = timezone.now()
        for field, value in (("ended_at", now), ("revoked_at", now)):
            if hasattr(us, field):
                setattr(us, field, value)
        for field, value in (
            ("ended_reason", reason),
            ("revoked_reason", reason),
        ):
            if hasattr(us, field):
                setattr(us, field, value)
        if hasattr(us, "ended") and not getattr(us, "ended", False):
            us.ended = True
        us.save()

        UserSessionMeta.objects.update_or_create(
            user=user,
            session_key=us.session_key,
            defaults={"revoked_at": now, "revoked_reason": reason},
        )

        SessionService._blacklist_session_tokens(user, us.session_key, now)
        SessionService._kill_django_session(request, us.session_key)

        return {
            "ok": True,
            "id": us.session_key,
            "revoked_reason": getattr(us, "ended_reason", None)
            or getattr(us, "revoked_reason", reason),
            "revoked_at": getattr(us, "ended_at", None)
            or getattr(us, "revoked_at", now),
        }
