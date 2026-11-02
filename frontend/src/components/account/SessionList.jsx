import { Button, Label } from "@gravity-ui/uikit";

function deviceName(ua = "") {
  const browser = /Edg\//.test(ua)
    ? "Edge"
    : /Firefox\//.test(ua)
      ? "Firefox"
      : /Chrome\//.test(ua)
        ? "Chrome"
        : /Safari\//.test(ua)
          ? "Safari"
          : "Браузер";
  const system = /Android/.test(ua)
    ? "Android"
    : /iPhone|iPad/.test(ua)
      ? "iOS"
      : /Windows/.test(ua)
        ? "Windows"
        : /Macintosh|Mac OS/.test(ua)
          ? "macOS"
          : /Linux/.test(ua)
            ? "Linux"
            : "";
  return ua
    ? [browser, system].filter(Boolean).join(" · ")
    : "Неизвестное устройство";
}
function date(value) {
  const parsed = new Date(value);
  return value && Number.isFinite(parsed.getTime())
    ? parsed.toLocaleString("ru-RU")
    : "Не указано";
}
export default function SessionList({ sessions, busy, onRevoke, onSignout }) {
  return (
    <div className="security-session-list">
      {sessions.map((session) => (
        <article className="security-device-row" key={session.id}>
          <div className="security-device-copy">
            <div className="security-device-title">
              <strong>{deviceName(session.user_agent)}</strong>
              {session.current && !session.revoked && (
                <Label theme="success">Это устройство</Label>
              )}
              {session.revoked && <Label theme="normal">Сеанс завершён</Label>}
            </div>
            <span className="security-device-meta">
              Последняя активность: {date(session.last_seen || session.created)}
            </span>
            <details className="security-device-meta">
              <summary>Сведения о сеансе</summary>
              <p>IP: {session.ip || "Не указан"}</p>
              <p>Истекает: {date(session.expires)}</p>
              {session.user_agent && <p>{session.user_agent}</p>}
            </details>
          </div>
          {!session.revoked && (
            <div className="security-device-actions">
              <Button
                view={session.current ? "flat" : "outlined"}
                disabled={busy}
                onClick={() =>
                  session.current ? onSignout() : onRevoke(session.id)
                }
                extraProps={{
                  "aria-label": session.current
                    ? "Выйти на этом устройстве"
                    : `Завершить сеанс ${deviceName(session.user_agent)}`,
                }}
              >
                {session.current ? "Выйти здесь" : "Завершить сеанс"}
              </Button>
            </div>
          )}
        </article>
      ))}
    </div>
  );
}
