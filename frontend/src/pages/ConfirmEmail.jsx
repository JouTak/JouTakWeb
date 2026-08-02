import { Button, Loader } from "@gravity-ui/uikit";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import {
  PageActions,
  PageNotice,
  PagePanel,
  PageShell,
} from "../components/ui/PageShell.jsx";
import {
  confirmEmailVerification,
  hasStoredAuth,
  inspectEmailVerification,
} from "../services/api";
import { extractErrorMessage } from "../services/errors";
import styles from "./SystemPages.module.css";

export default function ConfirmEmail() {
  const location = useLocation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const key = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return (params.get("key") || "").trim();
  }, [location.search]);
  const isAuthenticated = hasStoredAuth();
  const accountPath = isAuthenticated ? "/account/security" : "/login";

  useEffect(() => {
    let active = true;

    async function load() {
      if (!key) {
        setError("В ссылке отсутствует ключ подтверждения email.");
        setLoading(false);
        return;
      }

      setLoading(true);
      setError("");
      try {
        const response = await inspectEmailVerification(key);
        if (!active) {
          return;
        }
        setEmail(response?.data?.email || "");
      } catch (err) {
        if (!active) {
          return;
        }
        setError(
          extractErrorMessage(
            err,
            "Ссылка подтверждения недействительна или уже устарела.",
          ),
        );
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      active = false;
    };
  }, [key]);

  async function onConfirm() {
    setBusy(true);
    setError("");
    try {
      await confirmEmailVerification(key);
      setSuccess(true);
    } catch (err) {
      setError(
        extractErrorMessage(
          err,
          "Не удалось подтвердить email. Попробуйте запросить новое письмо.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell
      narrow
      eyebrow="Аккаунт"
      title="Подтверждение email"
      description="Проверяем ссылку и подтверждаем адрес, привязанный к аккаунту."
    >
      <PagePanel className={styles.stack} aria-busy={loading}>
        {loading ? (
          <div className={styles.loading} aria-live="polite">
            <Loader size="l" />
            <span>Проверяем ссылку подтверждения…</span>
          </div>
        ) : success ? (
          <>
            <PageNotice tone="success">
              Email подтверждён. Теперь аккаунт готов к защищённым сценариям.
            </PageNotice>
            <PageActions>
              <Button
                view="action"
                size="l"
                onClick={() => navigate(accountPath)}
              >
                {isAuthenticated ? "Перейти в аккаунт" : "Войти"}
              </Button>
              <Button view="outlined" size="l" onClick={() => navigate("/")}>
                На главную ITMOcraft
              </Button>
            </PageActions>
          </>
        ) : error ? (
          <>
            <PageNotice tone="danger">{error}</PageNotice>
            <p className={styles.message}>
              Ссылки подтверждения имеют ограниченный срок действия. Если адрес
              ещё не подтверждён, запроси новое письмо в настройках аккаунта.
            </p>
            <PageActions>
              <Button
                view="action"
                size="l"
                onClick={() => navigate(accountPath)}
              >
                {isAuthenticated ? "Вернуться в аккаунт" : "Ко входу"}
              </Button>
              <Button view="outlined" size="l" onClick={() => navigate("/")}>
                На главную
              </Button>
            </PageActions>
          </>
        ) : (
          <>
            <p className={styles.message}>
              {email
                ? `Подтверди адрес ${email}, чтобы завершить операцию.`
                : "Подтверди адрес электронной почты, чтобы завершить операцию."}
            </p>
            <PageActions>
              <Button view="action" size="l" loading={busy} onClick={onConfirm}>
                Подтвердить email
              </Button>
              <Button
                view="outlined"
                size="l"
                disabled={busy}
                onClick={() => navigate("/")}
              >
                Отмена
              </Button>
            </PageActions>
          </>
        )}
      </PagePanel>
    </PageShell>
  );
}
