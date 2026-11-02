import { Button } from "@gravity-ui/uikit";
import { useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { safeInternalPath } from "../services/urlSafety";

const reasonText = {
  mfa_required: "Завершите проверку входа, чтобы открыть этот раздел.",
  auth_required:
    "Эта страница доступна только после авторизации. Войдите, чтобы продолжить.",
  MISSING_REFRESH:
    "Срок действия сессии завершился. Для продолжения необходимо войти снова.",
  REFRESH_FAILED:
    "Срок действия сессии завершился. Для продолжения необходимо войти снова.",
  SESSION_UNAUTHORIZED:
    "Срок действия сессии завершился. Для продолжения необходимо войти снова.",
  PASSWORD_CHANGED:
    "Пароль был изменён. Для продолжения необходимо войти снова.",
};

export default function SessionExpired() {
  const navigate = useNavigate();
  const location = useLocation();

  const { nextPath, reason } = useMemo(() => {
    const params = new URLSearchParams(location.search);
    const next = safeInternalPath(params.get("next") || "/joutak");
    const r = params.get("reason") || "SESSION_UNAUTHORIZED";
    return {
      nextPath: next,
      reason: r,
    };
  }, [location.search]);

  const message = reasonText[reason] || reasonText.SESSION_UNAUTHORIZED;

  return (
    <section
      style={{
        maxWidth: 760,
        margin: "0 auto",
        border: "1px solid rgba(255,255,255,0.12)",
        borderRadius: 12,
        padding: 20,
        display: "grid",
        gap: 12,
      }}
    >
      <h1 style={{ margin: 0 }}>
        {reason === "auth_required"
          ? "Войдите, чтобы продолжить"
          : reason === "mfa_required"
            ? "Подтвердите вход"
            : "Войдите снова"}
      </h1>
      <p style={{ margin: 0, opacity: 0.9 }}>{message}</p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Button
          view="action"
          onClick={() =>
            navigate(`/login?next=${encodeURIComponent(nextPath)}`)
          }
        >
          {reason === "auth_required"
            ? "Войти"
            : reason === "mfa_required"
              ? "Продолжить проверку"
              : "Войти снова"}
        </Button>
        <Button view="outlined" onClick={() => navigate("/joutak")}>
          На главную
        </Button>
      </div>
    </section>
  );
}
