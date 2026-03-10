import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { Modal, Button, TextInput, useToaster } from "@gravity-ui/uikit";
import { useNavigate } from "react-router-dom";
import {
  doLogin,
  doSignupAndLogin,
  me,
  requestPasswordReset,
} from "../services/api";
import { needsPersonalization } from "../utils/profileState";

function isSafeInternalPath(path) {
  return (
    typeof path === "string" &&
    path.startsWith("/") &&
    !path.startsWith("//")
  );
}

function extractErrorMessage(error, fallback) {
  const data = error?.response?.data;
  if (Array.isArray(data?.errors)) {
    const firstError = data.errors.find(
      (entry) => entry && typeof entry.message === "string" && entry.message.trim(),
    );
    if (firstError?.message) return firstError.message;
  }
  if (data?.fields && typeof data.fields === "object") {
    const firstFieldMessage = Object.values(data.fields).find(
      (value) => typeof value === "string" && value.trim(),
    );
    if (firstFieldMessage) return firstFieldMessage;
  }
  if (data?.errors && typeof data.errors === "object") {
    for (const entries of Object.values(data.errors)) {
      if (!Array.isArray(entries)) continue;
      const first = entries.find(
        (entry) =>
          entry &&
          typeof entry === "object" &&
          typeof entry.message === "string" &&
          entry.message.trim(),
      );
      if (first?.message) return first.message;
    }
  }
  return data?.detail || data?.message || fallback;
}

export default function AuthModal({
  open = false,
  onClose,
  successRedirectTo = null,
}) {
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [busy, setBusy] = useState(false);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [suUsername, setSuUsername] = useState("");
  const [suEmail, setSuEmail] = useState("");
  const [suPassword, setSuPassword] = useState("");
  const [suPassword2, setSuPassword2] = useState("");
  const [resetEmail, setResetEmail] = useState("");
  const [resetError, setResetError] = useState("");
  const [resetSuccess, setResetSuccess] = useState("");

  const toaster = useToaster();
  const isLogin = mode === "login";
  const isResetPassword = mode === "reset-password";
  const title = useMemo(() => {
    if (isResetPassword) return "Сброс пароля";
    if (isLogin) return "Вход";
    return "Регистрация";
  }, [isLogin, isResetPassword]);
  const safeSuccessRedirectTo = useMemo(() => {
    if (isSafeInternalPath(successRedirectTo)) return successRedirectTo;
    return null;
  }, [successRedirectTo]);

  function resetForms() {
    setUsername("");
    setPassword("");
    setSuUsername("");
    setSuEmail("");
    setSuPassword("");
    setSuPassword2("");
    setResetEmail("");
    setResetError("");
    setResetSuccess("");
  }

  function close({ notifyParent = true } = {}) {
    resetForms();
    setBusy(false);
    if (notifyParent) onClose?.();
  }

  useEffect(() => {
    if (!open) {
      resetForms();
      setMode("login");
      setBusy(false);
    }
  }, [open]);

  const emailOk = (s) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s);

  function validateLogin() {
    if (!username.trim()) return "Укажите логин.";
    if (!password) return "Введите пароль.";
    return null;
  }

  function validateSignup() {
    if (!suUsername.trim()) return "Укажите имя пользователя.";
    if (!suEmail.trim()) return "Укажите email.";
    if (!emailOk(suEmail)) return "Неверный формат email.";
    if (!suPassword) return "Введите пароль.";
    if (suPassword.length < 8) return "Минимальная длина пароля — 8 символов.";
    if (suPassword2 !== suPassword) return "Пароли не совпадают.";
    return null;
  }

  async function onResetRequestSubmit(e) {
    e.preventDefault();
    const trimmedEmail = String(resetEmail || "").trim();
    if (!trimmedEmail) {
      setResetError("Укажите email.");
      return;
    }
    if (!emailOk(trimmedEmail)) {
      setResetError("Неверный формат email.");
      return;
    }

    setBusy(true);
    setResetError("");
    try {
      await requestPasswordReset(trimmedEmail);
      setResetSuccess(
        "Если аккаунт с таким email существует, мы отправили письмо со ссылкой для сброса пароля.",
      );
    } catch (ex) {
      setResetError(
        extractErrorMessage(
          ex,
          "Не удалось отправить письмо для сброса пароля.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  async function onLoginSubmit(e) {
    e.preventDefault();
    const err = validateLogin();
    if (err) return toaster.add({ title: err, theme: "warning" });
    setBusy(true);
    try {
      await doLogin({ username, password });
      const p = await me();
      toaster.add({
        title: "Готово!",
        content: `Здравствуйте, ${p.username}.`,
        theme: "success",
      });
      if (needsPersonalization(p)) {
        toaster.add({
          title: "Нужна персонализация профиля",
          content:
            "Чтобы открыть полный функционал, заполни обязательные поля профиля.",
          theme: "warning",
        });
        close({ notifyParent: !safeSuccessRedirectTo });
        navigate("/account/complete-profile", { replace: true });
        return;
      }
      if (safeSuccessRedirectTo) {
        resetForms();
        setBusy(false);
        navigate(safeSuccessRedirectTo, { replace: true });
        return;
      }
      close();
    } catch (ex) {
      toaster.add({
        title: extractErrorMessage(ex, "Ошибка входа"),
        theme: "danger",
      });
    } finally {
      setBusy(false);
    }
  }

  async function onSignupSubmit(e) {
    e.preventDefault();
    const err = validateSignup();
    if (err) return toaster.add({ title: err, theme: "warning" });
    setBusy(true);
    try {
      await doSignupAndLogin({
        username: suUsername.trim(),
        email: suEmail.trim(),
        password: suPassword,
      });
      const p = await me();
      toaster.add({
        title: "Аккаунт создан",
        content: `Добро пожаловать, ${p.username}!`,
        theme: "success",
      });
      if (needsPersonalization(p)) {
        close({ notifyParent: !safeSuccessRedirectTo });
        navigate("/account/complete-profile", { replace: true });
        return;
      }
      if (safeSuccessRedirectTo) {
        resetForms();
        setBusy(false);
        navigate(safeSuccessRedirectTo, { replace: true });
        return;
      }
      close();
    } catch (ex) {
      toaster.add({
        title: extractErrorMessage(ex, "Ошибка регистрации"),
        theme: "danger",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={close}
      aria-labelledby="auth-modal-title"
      disableBodyScrollLock
      style={{ "--g-modal-width": "520px" }}
    >
      <div style={{ padding: 24, display: "grid", gap: 16 }}>
        <h3 id="auth-modal-title" style={{ margin: 0 }}>
          {title}
        </h3>

        {isLogin ? (
          <form onSubmit={onLoginSubmit} style={{ display: "grid", gap: 12 }}>
            <TextInput
              size="l"
              label="Никнейм"
              value={username}
              onUpdate={setUsername}
              name="joutak__username"
              autoComplete="username"
              autoFocus
              disabled={busy}
            />
            <TextInput
              size="l"
              type="password"
              label="Пароль"
              value={password}
              onUpdate={setPassword}
              name="joutak__password"
              autoComplete="current-password"
              disabled={busy}
            />
            <Button
              view="action"
              size="l"
              loading={busy}
              width="max"
              type="submit"
            >
              Войти
            </Button>

            <Button
              view="outlined"
              size="l"
              width="max"
              onClick={() => setMode("signup")}
            >
              Нет аккаунта? Зарегистрируйтесь
            </Button>

            <Button
              view="flat"
              size="l"
              width="max"
              type="button"
              onClick={() => {
                setResetError("");
                setResetSuccess("");
                setResetEmail("");
                setMode("reset-password");
              }}
            >
              Забыли пароль?
            </Button>

            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                marginTop: 4,
              }}
            >
              <Button view="flat" onClick={close}>
                Закрыть
              </Button>
            </div>
          </form>
        ) : isResetPassword ? (
          <div style={{ display: "grid", gap: 12 }}>
            <p style={{ margin: 0, opacity: 0.9 }}>
              Укажите email, и мы отправим письмо со ссылкой для сброса пароля.
            </p>

            {resetSuccess ? (
              <>
                <p style={{ margin: 0, opacity: 0.9 }}>{resetSuccess}</p>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <Button view="action" onClick={() => setMode("login")}>
                    Вернуться ко входу
                  </Button>
                  <Button
                    view="outlined"
                    type="button"
                    onClick={() => {
                      setResetSuccess("");
                      setResetError("");
                    }}
                  >
                    Отправить ещё раз
                  </Button>
                </div>
              </>
            ) : (
              <form
                onSubmit={onResetRequestSubmit}
                style={{ display: "grid", gap: 12 }}
              >
                <TextInput
                  size="l"
                  type="email"
                  label="Email"
                  value={resetEmail}
                  onUpdate={setResetEmail}
                  autoComplete="email"
                  autoFocus
                  disabled={busy}
                />
                {resetError && (
                  <p style={{ margin: 0, color: "#ff8e8e" }}>{resetError}</p>
                )}
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <Button view="action" type="submit" loading={busy}>
                    Отправить письмо
                  </Button>
                  <Button
                    view="outlined"
                    type="button"
                    onClick={() => {
                      setResetError("");
                      setMode("login");
                    }}
                  >
                    Назад ко входу
                  </Button>
                </div>
              </form>
            )}

            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                marginTop: 4,
              }}
            >
              <Button view="flat" onClick={close}>
                Закрыть
              </Button>
            </div>
          </div>
        ) : (
          <form onSubmit={onSignupSubmit} style={{ display: "grid", gap: 12 }}>
            <TextInput
              size="l"
              label="Никнейм"
              value={suUsername}
              onUpdate={setSuUsername}
              name="joutak__username"
              autoComplete="username"
              disabled={busy}
            />
            <TextInput
              size="l"
              type="email"
              label="Email"
              value={suEmail}
              onUpdate={setSuEmail}
              name="joutak__email"
              autoComplete="email"
              disabled={busy}
            />
            <TextInput
              size="l"
              type="password"
              label="Пароль"
              value={suPassword}
              onUpdate={setSuPassword}
              name="joutak__password"
              autoComplete="new-password"
              disabled={busy}
            />
            <TextInput
              size="l"
              type="password"
              label="Повторите пароль"
              value={suPassword2}
              onUpdate={setSuPassword2}
              name="joutak__password"
              autoComplete="new-password"
              disabled={busy}
            />
            <Button
              view="action"
              size="l"
              loading={busy}
              width="max"
              type="submit"
            >
              Создать аккаунт
            </Button>
            <Button
              view="outlined"
              size="l"
              width="max"
              onClick={() => setMode("login")}
            >
              У меня уже есть аккаунт
            </Button>
            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                marginTop: 4,
              }}
            >
              <Button view="flat" onClick={close}>
                Закрыть
              </Button>
            </div>
          </form>
        )}
      </div>
    </Modal>
  );
}

AuthModal.propTypes = {
  open: PropTypes.bool,
  onClose: PropTypes.func,
  successRedirectTo: PropTypes.string,
};
