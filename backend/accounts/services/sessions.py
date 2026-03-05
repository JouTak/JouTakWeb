from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from accounts.transport.schemas import RevokeSessionsIn, SessionRowOut
from allauth.account.adapter import get_adapter as get_account_adapter
from allauth.usersessions.models import UserSession
from core.models import UserSessionMeta, UserSessionToken
from django.contrib.auth import get_user_model
from django.contrib.auth import logout as dj_logout
from django.contrib.sessions.models import Session
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from ninja.errors import HttpError
from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken

User = get_user_model()
UNKNOWN_IP_FALLBACK = "0.0.0.0"


@dataclass(slots=True)
class SessionService:
    @staticmethod
    def _client_ip(request: HttpRequest) -> str | None:
        return get_account_adapter().get_client_ip(request)

    @staticmethod
    def _ua(request: HttpRequest) -> str:
        return (request.META.get("HTTP_USER_AGENT", "") or "")[:512]

    @staticmethod
    def _header_token(request: HttpRequest) -> str:
        return request.headers.get("X-Session-Token") or ""

    @staticmethod
    def _session_key(request: HttpRequest) -> str:
        return request.session.session_key or ""

    @staticmethod
    def assert_session_allowed(request: HttpRequest) -> None:
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
    def _resolve_meta_for_touch(
        user: User,
        token: str,
        dj_key: str,
    ) -> UserSessionMeta:
        key_for_meta = dj_key or token
        meta, _ = UserSessionMeta.objects.select_for_update().get_or_create(
            user=user,
            session_key=key_for_meta,
            defaults={"session_token": token or None},
        )
        return meta

    @staticmethod
    def _update_meta_last_seen(
        meta: UserSessionMeta,
        request: HttpRequest,
        *,
        token: str,
        now: datetime,
        throttle_seconds: int,
    ) -> None:
        update_fields: list[str] = []
        if token and not meta.session_token:
            meta.session_token = token
            update_fields.append("session_token")

        should_refresh = (
            not meta.last_seen
            or (now - meta.last_seen).total_seconds() >= throttle_seconds
        )
        if should_refresh:
            meta.last_seen = now
            update_fields.append("last_seen")
            if not meta.user_agent:
                meta.user_agent = SessionService._ua(request)
                update_fields.append("user_agent")
            if not meta.ip:
                meta.ip = SessionService._client_ip(request)
                update_fields.append("ip")

        if update_fields:
            meta.save(update_fields=sorted(set(update_fields)))

    @staticmethod
    def _user_session_create_defaults(
        meta: UserSessionMeta,
        *,
        now: datetime,
    ) -> dict[str, object]:
        field_names = {field.name for field in UserSession._meta.fields}
        candidates: dict[str, object] = {
            "ip": meta.ip or UNKNOWN_IP_FALLBACK,
            "user_agent": meta.user_agent or "",
            "data": {},
            "last_seen_at": now,
        }
        return {
            field: value
            for field, value in candidates.items()
            if field in field_names
        }

    @staticmethod
    def _apply_user_session_timestamps(
        us: UserSession,
        *,
        now: datetime,
        created: bool,
    ) -> bool:
        changed = False
        for field, value in (
            ("last_seen", now),
            ("updated_at", now),
            ("last_seen_at", now),
        ):
            if hasattr(us, field):
                setattr(us, field, value)
                changed = True
        if created:
            for field, value in (("started_at", now), ("created", now)):
                if hasattr(us, field):
                    setattr(us, field, value)
                    changed = True
        return changed

    @staticmethod
    def _apply_user_session_meta(
        us: UserSession,
        meta: UserSessionMeta,
    ) -> bool:
        changed = False
        if hasattr(us, "user_agent") and not getattr(us, "user_agent", None):
            us.user_agent = meta.user_agent or ""
            changed = True
        ip_value = meta.ip or UNKNOWN_IP_FALLBACK
        if hasattr(us, "ip") and not getattr(us, "ip", None):
            us.ip = ip_value
            changed = True
        elif hasattr(us, "ip_address") and not getattr(us, "ip_address", None):
            us.ip_address = ip_value
            changed = True
        return changed

    @staticmethod
    def _sync_user_session_row(
        user: User,
        *,
        dj_key: str,
        meta: UserSessionMeta,
        now: datetime,
    ) -> None:
        defaults = SessionService._user_session_create_defaults(
            meta,
            now=now,
        )
        us, created = UserSession.objects.get_or_create(
            user=user,
            session_key=dj_key,
            defaults=defaults,
        )
        changed = SessionService._apply_user_session_timestamps(
            us,
            now=now,
            created=created,
        )
        if SessionService._apply_user_session_meta(us, meta):
            changed = True
        if changed:
            us.save()

    @staticmethod
    @transaction.atomic
    def touch(
        request: HttpRequest,
        user: User,
        *,
        throttle_seconds: int = 15,
    ) -> None:
        token = SessionService._header_token(request)
        dj_key = SessionService._session_key(request)
        if not (token or dj_key):
            return
        if not getattr(user, "is_authenticated", False):
            return

        now = timezone.now()
        meta = SessionService._resolve_meta_for_touch(user, token, dj_key)
        SessionService._update_meta_last_seen(
            meta,
            request,
            token=token,
            now=now,
            throttle_seconds=throttle_seconds,
        )

        if dj_key:
            SessionService._sync_user_session_row(
                user,
                dj_key=dj_key,
                meta=meta,
                now=now,
            )

    @staticmethod
    def _compose_row(
        request: HttpRequest,
        us: UserSession | None,
        meta: UserSessionMeta | None,
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
        request: HttpRequest,
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
    def list(request: HttpRequest, user: User) -> list[SessionRowOut]:
        us_rows = list(UserSession.objects.purge_and_list(user))
        meta_rows = list(UserSessionMeta.objects.filter(user=user))
        return SessionService._merge_rows(request, us_rows, meta_rows)

    @staticmethod
    def _blacklist_session_tokens(
        user: User,
        session_key: str,
        when: datetime,
    ) -> None:
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
    def _kill_django_session(
        request: HttpRequest,
        session_key: str,
    ) -> None:
        Session.objects.filter(session_key=session_key).delete()
        if SessionService._session_key(request) == session_key:
            dj_logout(request)

    @staticmethod
    def _validate_revoke_bulk_scope(
        ids: list[str],
        *,
        all_except_current: bool,
    ) -> None:
        if ids and all_except_current:
            raise HttpError(
                400, "Use either ids or all_except_current, not both"
            )
        if not ids and not all_except_current:
            raise HttpError(
                400, "Either ids or all_except_current=true is required"
            )

    @staticmethod
    def _resolve_current_session_key(
        request: HttpRequest,
        user: User,
    ) -> str:
        token = SessionService._header_token(request)
        cur_meta = UserSessionMeta.objects.filter(
            user=user, session_token=token
        ).first()
        return SessionService._session_key(request) or (
            cur_meta.session_key if cur_meta else ""
        )

    @staticmethod
    def _candidate_session_keys(
        user: User,
        ids: list[str],
        *,
        all_except_current: bool,
        current_key: str,
    ) -> list[str]:
        keys = set(
            UserSession.objects.filter(user=user).values_list(
                "session_key", flat=True
            )
        )
        keys.update(
            UserSessionMeta.objects.filter(user=user).values_list(
                "session_key", flat=True
            )
        )
        if ids:
            keys &= set(ids)
        elif all_except_current and current_key:
            keys.discard(current_key)
        return sorted(key for key in keys if key)

    @staticmethod
    def _revoke_session_key(
        request: HttpRequest,
        *,
        user: User,
        session_key: str,
        reason: str,
        now: datetime,
    ) -> None:
        us = UserSession.objects.filter(
            user=user, session_key=session_key
        ).first()
        if us:
            us.end()

        UserSessionMeta.objects.update_or_create(
            user=user,
            session_key=session_key,
            defaults={"revoked_at": now, "revoked_reason": reason},
        )
        SessionService._blacklist_session_tokens(user, session_key, now)
        if SessionService._session_key(request) == session_key:
            dj_logout(request)
        elif not us:
            SessionService._kill_django_session(request, session_key)

    @staticmethod
    def revoke_bulk(
        request: HttpRequest,
        payload: RevokeSessionsIn,
    ) -> dict[str, object]:
        SessionService.assert_session_allowed(request)
        user: User = request.auth
        SessionService.touch(request, user)
        ids = payload.ids or []
        SessionService._validate_revoke_bulk_scope(
            ids, all_except_current=payload.all_except_current
        )

        cur_key = SessionService._resolve_current_session_key(request, user)
        reason = (payload.reason or "bulk_except_current").lower()
        session_keys = SessionService._candidate_session_keys(
            user,
            ids,
            all_except_current=payload.all_except_current,
            current_key=cur_key,
        )

        now = timezone.now()
        revoked_ids, skipped_ids = [], []

        for session_key in session_keys:
            meta = UserSessionMeta.objects.filter(
                user=user, session_key=session_key
            ).first()
            us = UserSession.objects.filter(
                user=user, session_key=session_key
            ).first()
            if bool(meta and meta.revoked_at) and not (us and us.exists()):
                skipped_ids.append(session_key)
                continue
            SessionService._revoke_session_key(
                request,
                user=user,
                session_key=session_key,
                reason=reason,
                now=now,
            )
            revoked_ids.append(session_key)

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
        request: HttpRequest,
        *,
        sid: str,
        reason: str | None = None,
    ) -> dict[str, object]:
        SessionService.assert_session_allowed(request)
        user: User = request.auth
        SessionService.touch(request, user)
        reason = (reason or "manual").lower()

        us = UserSession.objects.filter(user=user, session_key=sid).first()
        meta = UserSessionMeta.objects.filter(
            user=user, session_key=sid
        ).first()
        if not us and not meta:
            raise HttpError(404, "session not found")

        now = timezone.now()
        SessionService._revoke_session_key(
            request,
            user=user,
            session_key=sid,
            reason=reason,
            now=now,
        )

        return {
            "ok": True,
            "id": sid,
            "revoked_reason": (
                (getattr(us, "ended_reason", None) if us else None)
                or (getattr(us, "revoked_reason", None) if us else None)
                or (meta.revoked_reason if meta else None)
                or reason
            ),
            "revoked_at": now,
        }
