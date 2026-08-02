import { Button } from "@gravity-ui/uikit";
import { useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import {
  PageActions,
  PageNotice,
  PagePanel,
  PageShell,
} from "../components/ui/PageShell.jsx";

function safeInternalPath(path) {
  if (typeof path !== "string") return "/";
  if (!path.startsWith("/")) return "/";
  if (path.startsWith("//")) return "/";
  return path;
}

const reasonText = {
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
    const next = safeInternalPath(params.get("next") || "/");
    const r = params.get("reason") || "SESSION_UNAUTHORIZED";
    return {
      nextPath: next,
      reason: r,
    };
  }, [location.search]);

  const message = reasonText[reason] || reasonText.SESSION_UNAUTHORIZED;

  return (
    <PageShell
      narrow
      eyebrow="Безопасность аккаунта"
      title="Сессия завершена"
      description="Мы остановили текущую сессию, чтобы сохранить аккаунт в безопасности."
    >
      <PagePanel>
        <PageNotice tone="warning">{message}</PageNotice>
        <p>
          После входа мы вернём тебя на страницу, с которой был начат сценарий.
          Если завершение сессии оказалось неожиданным, проверь активные сеансы
          и включи двухфакторную аутентификацию в настройках аккаунта.
        </p>
        <PageActions>
          <Button
            view="action"
            size="l"
            onClick={() =>
              navigate(`/login?next=${encodeURIComponent(nextPath)}`)
            }
          >
            Войти снова
          </Button>
          <Button view="outlined" size="l" onClick={() => navigate("/")}>
            На главную ITMOcraft
          </Button>
        </PageActions>
      </PagePanel>
    </PageShell>
  );
}
