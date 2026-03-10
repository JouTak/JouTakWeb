import { useEffect, useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Label,
  Switch,
  Tooltip,
  DropdownMenu,
  Modal,
  Text,
} from "@gravity-ui/uikit";
import {
  listSessionsHeadless,
  revokeSessionHeadless,
  bulkRevokeSessionsHeadless,
  logout,
} from "../../services/api";

const cardStyle = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 12,
  padding: 16,
  display: "grid",
  gap: 12,
};

const rowBetween = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 12,
};

const WINDOW_HOURS = 48;

function shortUA(ua = "") {
  if (!ua) return "Неизвестное устройство";
  return ua.length > 96 ? `${ua.slice(0, 96)}…` : ua;
}

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

function SessionsCardSkeleton() {
  return (
    <div
      className="skeleton-block"
      style={{
        borderRadius: 12,
        border: "1px solid rgba(255,255,255,0.08)",
        padding: 16,
        display: "grid",
        gap: 14,
      }}
      aria-hidden="true"
    >
      <div style={{ ...rowBetween, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div style={{ display: "grid", gap: 10, minWidth: 220, flex: "1 1 280px" }}>
          <div className="skeleton-line" style={{ width: 110, height: 18 }} />
          <div className="skeleton-line" style={{ width: "70%" }} />
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            flexWrap: "wrap",
            justifyContent: "flex-end",
          }}
        >
          <div className="skeleton-line" style={{ width: 190, height: 28 }} />
          <div className="skeleton-line" style={{ width: 210, height: 28 }} />
        </div>
      </div>

      {Array.from({ length: 3 }).map((_, index) => (
        <div
          key={index}
          style={{
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 10,
            padding: 12,
            display: "grid",
            gap: 10,
          }}
        >
          <div style={{ ...rowBetween, alignItems: "flex-start", flexWrap: "wrap" }}>
            <div style={{ display: "grid", gap: 8, minWidth: 240, flex: "1 1 320px" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  flexWrap: "wrap",
                }}
              >
                <div className="skeleton-line" style={{ width: 118, height: 16 }} />
                <div className="skeleton-line" style={{ width: 72, height: 20 }} />
              </div>
              <div className="skeleton-line" style={{ width: "84%" }} />
              <div className="skeleton-line" style={{ width: "62%" }} />
              <div className="skeleton-line" style={{ width: "48%" }} />
            </div>
            <div
              style={{
                display: "flex",
                gap: 8,
                flexWrap: "wrap",
                justifyContent: "flex-end",
              }}
            >
              <div className="skeleton-line" style={{ width: 108, height: 32 }} />
              <div className="skeleton-line" style={{ width: 100, height: 32 }} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function reasonBadge(reason) {
  if (!reason) return null;
  const map = {
    manual: { text: "Ручное отключение", theme: "warning" },
    signout: { text: "Выход", theme: "info" },
    logged_out: { text: "Вышел", theme: "info" },
    expired: { text: "Истекла", theme: "utility" },
    revoked: { text: "Отозвана", theme: "danger" },
    bulk_except_current: { text: "Массово (кроме текущей)", theme: "info" },
  };
  const key = String(reason).toLowerCase();
  const r = map[key] || { text: String(reason), theme: "normal" };
  return (
    <Label size="s" theme={r.theme}>
      {r.text}
    </Label>
  );
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

export default function SessionsCard() {
  const navigate = useNavigate();
  const [allSessions, setAllSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
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
      const norm = (
        Array.isArray(raw) ? raw : raw?.results || raw?.sessions || []
      ).map(normalizeSession);
      setAllSessions(norm);
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
    load();
  }, [load]);

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
    setConfirmOpen(false);
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
      setConfirmAction(null);
      setTargetSessionId(null);
    }
  }

  return (
    <section style={cardStyle}>
      <div style={rowBetween}>
        <h3 style={{ margin: 0, fontSize: 18 }}>Сессии</h3>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <Tooltip content="Показывать завершённые за последние 48 часов">
            <Switch
              size="m"
              checked={showHistory}
              onUpdate={setShowHistory}
              content="Отобразить завершенные"
            />
          </Tooltip>
          <Button view="flat-danger" onClick={askRevokeAllExceptCurrent}>
            Завершить все (кроме текущей)
          </Button>
        </div>
      </div>

      <div style={{ opacity: 0.8 }}>
        Отображаем{" "}
        {showHistory
          ? "сессии за последние 48 часов (включая завершённые)"
          : "активные сессии за последние 48 часов"}
        .
      </div>

      {loading ? (
        <SessionsCardSkeleton />
      ) : sessions.length ? (
        <div style={{ display: "grid", gap: 8 }}>
          {sessions.map((s) => {
            const actions = [];
            if (s.current && !s.revoked) {
              actions.push({
                text: "Выйти здесь",
                theme: "danger",
                action: askSignoutCurrent,
              });
            }
            if (!s.current && !s.revoked) {
              actions.push({
                text: "Завершить",
                theme: "danger",
                action: () => askRevokeOne(s.id),
              });
            }
            return (
              <div
                key={s.id}
                style={{
                  ...rowBetween,
                  border: "1px solid rgba(255,255,255,0.12)",
                  borderRadius: 10,
                  padding: 12,
                  background: s.current
                    ? "rgba(13,148,16,0.08)"
                    : s.revoked
                      ? "rgba(239,68,68,0.08)"
                      : "transparent",
                }}
              >
                <div style={{ display: "grid", gap: 4 }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      flexWrap: "wrap",
                    }}
                  >
                    <b>{s.current ? "Это устройство" : "Устройство"}</b>
                    {s.current && (
                      <Label size="s" theme="success">
                        Текущая
                      </Label>
                    )}
                    {s.revoked && (
                      <Label size="s" theme="danger">
                        Завершена
                      </Label>
                    )}
                    {s.revoked && reasonBadge(s.revoked_reason)}
                  </div>
                  <div style={{ opacity: 0.7, fontSize: 12 }}>
                    {shortUA(s.user_agent)}
                  </div>
                  <div style={{ opacity: 0.7, fontSize: 12 }}>
                    Последняя активность:{" "}
                    {s.last_seen
                      ? new Date(s.last_seen).toLocaleString()
                      : s.created
                        ? new Date(s.created).toLocaleString()
                        : "—"}
                    {s.ip ? ` · IP: ${s.ip}` : ""}
                  </div>
                  <div style={{ opacity: 0.7, fontSize: 12 }}>
                    Истекает:{" "}
                    {s.expires ? new Date(s.expires).toLocaleString() : "—"}
                  </div>
                </div>

                <div style={{ display: "flex", gap: 8 }}>
                  {!s.current && !s.revoked && (
                    <Button
                      view="outlined-danger"
                      onClick={() => askRevokeOne(s.id)}
                    >
                      Завершить
                    </Button>
                  )}
                  <DropdownMenu
                    size="m"
                    renderSwitcher={(props) => (
                      <Button {...props} view="outlined">
                        Действия
                      </Button>
                    )}
                    items={
                      actions.length
                        ? actions
                        : [{ text: "Нет доступных действий", disabled: true }]
                    }
                    onItemClick={(item) => item.action?.()}
                  />
                </div>
              </div>
            );
          })}
          {msg && <div style={{ opacity: 0.8 }}>{msg}</div>}
        </div>
      ) : (
        <div style={{ opacity: 0.8 }}>
          {showHistory
            ? "Сессий за 48 часов не найдено."
            : "Активных сессий не найдено."}
        </div>
      )}

      <Modal open={confirmOpen} onClose={() => setConfirmOpen(false)} size="s">
        <div style={{ padding: 16, display: "grid", gap: 12 }}>
          <h4 style={{ margin: 0 }}>Подтвердите действие</h4>
          <Text>
            {confirmAction === "revoke-one" && "Завершить выбранную сессию?"}
            {confirmAction === "signout-current" &&
              "Выйти из аккаунта на этом устройстве?"}
            {confirmAction === "revoke-all-except-current" &&
              "Завершить все сессии, кроме текущей?"}
          </Text>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <Button view="flat" onClick={() => setConfirmOpen(false)}>
              Отмена
            </Button>
            <Button view="action" onClick={runConfirmed}>
              Подтвердить
            </Button>
          </div>
        </div>
      </Modal>
    </section>
  );
}
