import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Button, Loader, TextInput } from "@gravity-ui/uikit";
import {
  inspectPasswordResetKey,
  requestPasswordReset,
  resetPasswordByKey,
} from "../services/api";

const cardStyle = {
  maxWidth: 760,
  margin: "0 auto",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 12,
  padding: 20,
  display: "grid",
  gap: 12,
};

function extractErrorMessage(error, fallback) {
  const errors = error?.response?.data?.errors;
  if (Array.isArray(errors)) {
    const first = errors.find(
      (entry) =>
        entry &&
        typeof entry === "object" &&
        typeof entry.message === "string" &&
        entry.message.trim(),
    );
    if (first?.message) {
      return first.message;
    }
  }
  return error?.response?.data?.detail || fallback;
}

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
    <section style={cardStyle}>
      <h2 style={{ margin: 0 }}>
        {key ? "Задайте новый пароль" : "Сброс пароля"}
      </h2>

      {loading ? (
        <Loader size="m" />
      ) : key ? (
        <>
          {!keyReady && error ? (
            <>
              <p style={{ margin: 0, opacity: 0.9 }}>{error}</p>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Button
                  view="action"
                  onClick={() => navigate("/reset-password")}
                >
                  Запросить новое письмо
                </Button>
                <Button
                  view="outlined"
                  type="button"
                  onClick={() => navigate("/login")}
                >
                  Ко входу
                </Button>
              </div>
            </>
          ) : (
            <>
              {accountEmail && (
                <p style={{ margin: 0, opacity: 0.9 }}>
                  Аккаунт: <b>{accountEmail}</b>
                </p>
              )}
              {success ? (
                <>
                  <p style={{ margin: 0, opacity: 0.9 }}>{success}</p>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <Button view="action" onClick={() => navigate("/login")}>
                      Войти
                    </Button>
                    <Button
                      view="outlined"
                      type="button"
                      onClick={() => navigate("/joutak")}
                    >
                      На главную
                    </Button>
                  </div>
                </>
              ) : (
                <form
                  onSubmit={onResetPassword}
                  style={{ display: "grid", gap: 12 }}
                >
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
                  {error && (
                    <p style={{ margin: 0, color: "#ff8e8e" }}>{error}</p>
                  )}
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <Button view="action" type="submit" loading={busy}>
                      Сохранить пароль
                    </Button>
                    <Button
                      view="outlined"
                      type="button"
                      onClick={() => navigate("/joutak")}
                    >
                      Отмена
                    </Button>
                  </div>
                </form>
              )}
            </>
          )}
        </>
      ) : (
        <>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Укажите email, и мы отправим письмо со ссылкой для сброса пароля.
          </p>
          {success ? (
            <>
              <p style={{ margin: 0, opacity: 0.9 }}>{success}</p>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Button view="action" onClick={() => navigate("/login")}>
                  Вернуться ко входу
                </Button>
                <Button
                  view="outlined"
                  type="button"
                  onClick={() => setSuccess("")}
                >
                  Отправить ещё раз
                </Button>
              </div>
            </>
          ) : (
            <form
              onSubmit={onRequestReset}
              style={{ display: "grid", gap: 12 }}
            >
              <TextInput
                size="l"
                type="email"
                label="Email"
                value={email}
                onUpdate={setEmail}
                autoComplete="email"
                disabled={busy}
              />
              {error && <p style={{ margin: 0, color: "#ff8e8e" }}>{error}</p>}
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Button view="action" type="submit" loading={busy}>
                  Отправить письмо
                </Button>
                <Button
                  view="outlined"
                  type="button"
                  onClick={() => navigate("/login")}
                >
                  Назад ко входу
                </Button>
              </div>
            </form>
          )}
        </>
      )}
    </section>
  );
}
