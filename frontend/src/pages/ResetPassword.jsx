import { Button, Loader, TextInput } from "@gravity-ui/uikit";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import {
  PageActions,
  PageNotice,
  PagePanel,
  PageShell,
} from "../components/ui/PageShell.jsx";
import {
  inspectPasswordResetKey,
  requestPasswordReset,
  resetPasswordByKey,
} from "../services/api";
import { extractErrorMessage } from "../services/errors";
import styles from "./SystemPages.module.css";

function emailOk(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || "").trim());
}

export default function ResetPassword() {
  const location = useLocation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [keyReady, setKeyReady] = useState(false);
  const [email, setEmail] = useState("");
  const [accountEmail, setAccountEmail] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");

  const key = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return (params.get("key") || "").trim();
  }, [location.search]);

  useEffect(() => {
    let active = true;

    async function load() {
      if (!key) {
        setLoading(false);
        setError("");
        setKeyReady(false);
        return;
      }

      setLoading(true);
      setError("");
      setSuccess("");
      setKeyReady(false);
      try {
        const response = await inspectPasswordResetKey(key);
        if (!active) {
          return;
        }
        setKeyReady(true);
        setAccountEmail(response?.data?.user?.email || "");
      } catch (err) {
        if (!active) {
          return;
        }
        setError(
          extractErrorMessage(
            err,
            "Ссылка для сброса пароля недействительна или уже устарела.",
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

  async function onRequestReset(evt) {
    evt.preventDefault();
    const trimmedEmail = String(email || "").trim();
    if (!trimmedEmail) {
      setError("Укажите email.");
      return;
    }
    if (!emailOk(trimmedEmail)) {
      setError("Неверный формат email.");
      return;
    }

    setBusy(true);
    setError("");
    try {
      await requestPasswordReset(trimmedEmail);
      setSuccess(
        "Если аккаунт с таким email существует, мы отправили письмо со ссылкой для сброса пароля.",
      );
    } catch (err) {
      setError(
        extractErrorMessage(
          err,
          "Не удалось отправить письмо для сброса пароля.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  async function onResetPassword(evt) {
    evt.preventDefault();
    if (!password) {
      setError("Введите новый пароль.");
      return;
    }
    if (password.length < 8) {
      setError("Минимальная длина пароля — 8 символов.");
      return;
    }
    if (password !== password2) {
      setError("Пароли не совпадают.");
      return;
    }

    setBusy(true);
    setError("");
    try {
      await resetPasswordByKey({ key, password });
      setSuccess("Пароль успешно обновлён. Теперь можно войти в аккаунт.");
    } catch (err) {
      setError(
        extractErrorMessage(
          err,
          "Не удалось обновить пароль. Запросите новое письмо для сброса.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell
      narrow
      eyebrow="Безопасность аккаунта"
      title={key ? "Новый пароль" : "Сброс пароля"}
      description={
        key
          ? "Проверяем ссылку и безопасно обновляем данные для входа."
          : "Отправим одноразовую ссылку на email, связанный с аккаунтом."
      }
    >
      <PagePanel className={styles.stack} aria-busy={loading}>
        {loading ? (
          <div className={styles.loading} aria-live="polite">
            <Loader size="l" />
            <span>Проверяем ссылку сброса…</span>
          </div>
        ) : key ? (
          !keyReady && error ? (
            <>
              <PageNotice tone="danger">{error}</PageNotice>
              <PageActions>
                <Button
                  view="action"
                  size="l"
                  onClick={() => navigate("/reset-password")}
                >
                  Запросить новое письмо
                </Button>
                <Button
                  view="outlined"
                  size="l"
                  type="button"
                  onClick={() => navigate("/login")}
                >
                  Ко входу
                </Button>
              </PageActions>
            </>
          ) : (
            <>
              {accountEmail && (
                <div className={styles.identity}>
                  Аккаунт: <b>{accountEmail}</b>
                </div>
              )}
              {success ? (
                <>
                  <PageNotice tone="success">{success}</PageNotice>
                  <PageActions>
                    <Button
                      view="action"
                      size="l"
                      onClick={() => navigate("/login")}
                    >
                      Войти
                    </Button>
                    <Button
                      view="outlined"
                      size="l"
                      type="button"
                      onClick={() => navigate("/")}
                    >
                      На главную
                    </Button>
                  </PageActions>
                </>
              ) : (
                <form onSubmit={onResetPassword} className={styles.form}>
                  <TextInput
                    size="l"
                    type="password"
                    label="Новый пароль"
                    value={password}
                    onUpdate={setPassword}
                    autoComplete="new-password"
                    disabled={busy}
                  />
                  <TextInput
                    size="l"
                    type="password"
                    label="Повторите пароль"
                    value={password2}
                    onUpdate={setPassword2}
                    autoComplete="new-password"
                    disabled={busy}
                  />
                  {error && <PageNotice tone="danger">{error}</PageNotice>}
                  <PageActions>
                    <Button view="action" size="l" type="submit" loading={busy}>
                      Сохранить пароль
                    </Button>
                    <Button
                      view="outlined"
                      size="l"
                      type="button"
                      disabled={busy}
                      onClick={() => navigate("/")}
                    >
                      Отмена
                    </Button>
                  </PageActions>
                </form>
              )}
            </>
          )
        ) : (
          <>
            <p className={styles.message}>
              Укажи email — ответ будет одинаковым независимо от того, есть ли
              такой аккаунт. Это защищает данные пользователей.
            </p>
            {success ? (
              <>
                <PageNotice tone="success">{success}</PageNotice>
                <PageActions>
                  <Button
                    view="action"
                    size="l"
                    onClick={() => navigate("/login")}
                  >
                    Вернуться ко входу
                  </Button>
                  <Button
                    view="outlined"
                    size="l"
                    type="button"
                    onClick={() => setSuccess("")}
                  >
                    Отправить ещё раз
                  </Button>
                </PageActions>
              </>
            ) : (
              <form onSubmit={onRequestReset} className={styles.form}>
                <TextInput
                  size="l"
                  type="email"
                  label="Email"
                  value={email}
                  onUpdate={setEmail}
                  autoComplete="email"
                  disabled={busy}
                />
                {error && <PageNotice tone="danger">{error}</PageNotice>}
                <PageActions>
                  <Button view="action" size="l" type="submit" loading={busy}>
                    Отправить письмо
                  </Button>
                  <Button
                    view="outlined"
                    size="l"
                    type="button"
                    disabled={busy}
                    onClick={() => navigate("/login")}
                  >
                    Назад ко входу
                  </Button>
                </PageActions>
              </form>
            )}
          </>
        )}
      </PagePanel>
    </PageShell>
  );
}
