import { Button, Loader, Switch } from "@gravity-ui/uikit";
import PropTypes from "prop-types";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  bulkRevokeSessionsHeadless,
  listSessionsHeadless,
  logout,
  revokeSessionHeadless,
} from "../../services/api";
import { ConfirmDialog, SectionCard } from "../ui/primitives";
import SessionList from "./SessionList";

const WINDOW_HOURS = 48;

function sessionTimestamp(value) {
  const parsed = Date.parse(value || "");
  return Number.isFinite(parsed) ? parsed : 0;
}

function compareSessions(left, right) {
  if (left.current !== right.current) {
    return left.current ? -1 : 1;
  }
  if (left.revoked !== right.revoked) {
    return left.revoked ? 1 : -1;
  }

  const lastActivityDelta =
    sessionTimestamp(right.last_seen || right.created) -
    sessionTimestamp(left.last_seen || left.created);
  if (lastActivityDelta !== 0) {
    return lastActivityDelta;
  }

  const expiryDelta =
    sessionTimestamp(right.expires) - sessionTimestamp(left.expires);
  if (expiryDelta !== 0) {
    return expiryDelta;
  }

  return String(left.id || "").localeCompare(String(right.id || ""), "ru");
}

function normalizeSession(raw) {
  const id = String(
    raw.id ?? raw.session ?? raw.session_id ?? raw.session_key ?? raw.key ?? "",
  );
  const ua = raw.user_agent ?? raw.ua ?? "";
  const ip = raw.ip ?? raw.ip_address ?? raw.remote_addr ?? null;
  const created =
    raw.created ?? raw.created_at ?? raw.login_time ?? raw.start ?? null;
  const lastSeen =
    raw.last_seen ?? raw.last_activity ?? raw.updated_at ?? created ?? null;
  const expires = raw.expires ?? raw.expiry ?? raw.expire_at ?? null;
  const current = !!(raw.current ?? raw.is_current ?? raw.this_device ?? false);
  const ended =
    raw.revoked ??
    raw.ended ??
    raw.logged_out ??
    raw.is_terminated ??
    raw.is_expired ??
    false;
  const reason =
    raw.revoked_reason ??
    raw.reason ??
    (raw.is_expired ? "expired" : null) ??
    (raw.logged_out ? "logged_out" : null) ??
    null;

  return {
    id,
    user_agent: ua,
    ip,
    created,
    last_seen: lastSeen,
    expires,
    current,
    revoked: !!ended,
    revoked_reason: reason,
  };
}

function normalizeSessionList(payload) {
  const source = Array.isArray(payload)
    ? payload
    : payload?.results || payload?.sessions || [];
  return source.map(normalizeSession);
}

export default function SessionsCard({ initialSessions, embedded = false }) {
  const navigate = useNavigate();
  const [allSessions, setAllSessions] = useState(() =>
    initialSessions === undefined ? [] : normalizeSessionList(initialSessions),
  );
  const [loading, setLoading] = useState(initialSessions === undefined);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState(null);
  const [targetSessionId, setTargetSessionId] = useState(null);

  const redirectToSessionExpired = useCallback(() => {
    const params = new URLSearchParams({
      reason: "SESSION_UNAUTHORIZED",
      next: "/account/security",
    });
    navigate(`/session-expired?${params.toString()}`, { replace: true });
  }, [navigate]);

  const load = useCallback(async () => {
    setLoading(true);
    setMsg("");
    try {
      const raw = await listSessionsHeadless();
      setAllSessions(normalizeSessionList(raw));
    } catch (error) {
      if (error?.response?.status === 401) {
        redirectToSessionExpired();
        return;
      }
      setMsg("Не удалось загрузить список сессий.");
    } finally {
      setLoading(false);
    }
  }, [redirectToSessionExpired]);

  useEffect(() => {
    if (initialSessions !== undefined) {
      setAllSessions(normalizeSessionList(initialSessions));
      setLoading(false);
      setMsg("");
      return;
    }
    load();
  }, [initialSessions, load]);

  const sessions = useMemo(() => {
    const cutoff = Date.now() - WINDOW_HOURS * 3600 * 1000;
    return allSessions
      .filter((session) => {
        const ts = sessionTimestamp(session.last_seen || session.created);
        return ts >= cutoff || !ts;
      })
      .filter((session) => showHistory || !session.revoked)
      .sort(compareSessions);
  }, [allSessions, showHistory]);

  function askRevokeOne(id) {
    setConfirmAction("revoke-one");
    setTargetSessionId(id);
    setConfirmOpen(true);
  }
  function askSignoutCurrent() {
    setConfirmAction("signout-current");
    setTargetSessionId(null);
    setConfirmOpen(true);
  }
  function askRevokeAllExceptCurrent() {
    setConfirmAction("revoke-all-except-current");
    setTargetSessionId(null);
    setConfirmOpen(true);
  }

  async function revokeAllExceptCurrent() {
    const res = await bulkRevokeSessionsHeadless();
    const ids = new Set(res?.revoked_ids || []);
    setAllSessions((arr) =>
      arr.map((s) =>
        ids.has(s.id)
          ? { ...s, revoked: true, revoked_reason: "bulk_except_current" }
          : s,
      ),
    );
    return res;
  }

  async function runConfirmed() {
    if (busy) return;
    setBusy(true);
    try {
      if (confirmAction === "revoke-one" && targetSessionId) {
        const r = await revokeSessionHeadless(targetSessionId, "manual");
        setAllSessions((arr) =>
          arr.map((s) =>
            s.id === r.id
              ? {
                  ...s,
                  revoked: true,
                  revoked_reason: r.revoked_reason || "manual",
                }
              : s,
          ),
        );
        setMsg("Сессия завершена.");
      } else if (confirmAction === "signout-current") {
        await logout();
        setMsg("Вы вышли из аккаунта на этом устройстве.");
        redirectToSessionExpired();
      } else if (confirmAction === "revoke-all-except-current") {
        await revokeAllExceptCurrent();
        setMsg("Все сессии завершены, кроме текущей.");
      }
    } catch {
      setMsg("Операция не выполнена.");
    } finally {
      setBusy(false);
      setConfirmOpen(false);
      setConfirmAction(null);
      setTargetSessionId(null);
    }
  }

  return (
    <SectionCard plain={embedded}>
      {!embedded && (
        <h3 style={{ margin: 0, fontSize: 18 }}>Устройства и сеансы</h3>
      )}
      <div className="security-session-controls">
        <Switch
          checked={showHistory}
          onUpdate={setShowHistory}
          content="Показать завершённые за 48 часов"
        />
        <Button
          view="outlined"
          disabled={busy || !allSessions.some((s) => !s.current && !s.revoked)}
          onClick={askRevokeAllExceptCurrent}
        >
          Выйти на других устройствах
        </Button>
      </div>
      <p className="security-muted">
        Сеансы с активностью за последние 48 часов.
      </p>
      {loading ? (
        <Loader />
      ) : sessions.length ? (
        <SessionList
          sessions={sessions}
          busy={busy}
          onRevoke={askRevokeOne}
          onSignout={askSignoutCurrent}
        />
      ) : (
        <p className="security-muted">
          {showHistory
            ? "Сеансов за 48 часов не найдено."
            : "Активных сеансов за 48 часов не найдено."}
        </p>
      )}
      {msg && <p role="status">{msg}</p>}
      <ConfirmDialog
        open={confirmOpen}
        title={
          confirmAction === "signout-current"
            ? "Выйти на этом устройстве?"
            : confirmAction === "revoke-one"
              ? "Завершить этот сеанс?"
              : "Выйти на других устройствах?"
        }
        confirmText="Подтвердить"
        cancelText="Отмена"
        loading={busy}
        onCancel={() => {
          if (!busy) setConfirmOpen(false);
        }}
        onConfirm={runConfirmed}
      >
        <p>
          {confirmAction === "signout-current"
            ? "Для продолжения потребуется снова войти в аккаунт."
            : "На отключённых устройствах потребуется войти заново. Текущий сеанс сохранится."}
        </p>
      </ConfirmDialog>
    </SectionCard>
  );
}

SessionsCard.propTypes = {
  embedded: PropTypes.bool,
  initialSessions: PropTypes.oneOfType([
    PropTypes.arrayOf(PropTypes.object),
    PropTypes.shape({
      results: PropTypes.arrayOf(PropTypes.object),
      sessions: PropTypes.arrayOf(PropTypes.object),
    }),
  ]),
};
