import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { Modal, Button, TextInput, useToaster } from "@gravity-ui/uikit";
import { doLogin, doSignupAndLogin, me } from "../services/api";

export default function AuthModal({ open = false, onClose }) {
  const [mode, setMode] = useState("login");
  const [busy, setBusy] = useState(false);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [suUsername, setSuUsername] = useState("");
  const [suEmail, setSuEmail] = useState("");
  const [suPassword, setSuPassword] = useState("");
  const [suPassword2, setSuPassword2] = useState("");

  const toaster = useToaster();
  const isLogin = mode === "login";
  const title = useMemo(() => (isLogin ? "Вход" : "Регистрация"), [isLogin]);

  function resetForms() {
    setUsername("");
    setPassword("");
    setSuUsername("");
    setSuEmail("");
    setSuPassword("");
    setSuPassword2("");
  }

  function close() {
    resetForms();
    setBusy(false);
    onClose?.();
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
    if (password.length < 8) return "Минимальная длина пароля — 8 символов.";
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
      close();
    } catch (ex) {
      const r = ex?.response;
      const msg =
        r?.data?.errors?.[0]?.message ||
        r?.data?.detail ||
        r?.data?.message ||
        "Ошибка входа";
      toaster.add({ title: msg, theme: "danger" });
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
      close();
    } catch (ex) {
      const r = ex?.response;
      const msg =
        r?.data?.errors?.[0]?.message ||
        r?.data?.detail ||
        r?.data?.message ||
        "Ошибка регистрации";
      toaster.add({ title: msg, theme: "danger" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={close}
      aria-labelledby="auth-modal-title"
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
              name="username"
              autoComplete="username"
              autoFocus
              hasClear
              disabled={busy}
            />
            <TextInput
              size="l"
              type="password"
              label="Пароль"
              value={password}
              onUpdate={setPassword}
              name="current-password"
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
        ) : (
          <form onSubmit={onSignupSubmit} style={{ display: "grid", gap: 12 }}>
            <TextInput
              size="l"
              label="Никнейм"
              value={suUsername}
              onUpdate={setSuUsername}
              name="username"
              autoComplete="username"
              hasClear
              disabled={busy}
            />
            <TextInput
              size="l"
              type="email"
              label="Email"
              value={suEmail}
              onUpdate={setSuEmail}
              name="email"
              autoComplete="email"
              hasClear
              disabled={busy}
            />
            <TextInput
              size="l"
              type="password"
              label="Пароль"
              value={suPassword}
              onUpdate={setSuPassword}
              name="new-password"
              autoComplete="new-password"
              disabled={busy}
            />
            <TextInput
              size="l"
              type="password"
              label="Повторите пароль"
              value={suPassword2}
              onUpdate={setSuPassword2}
              name="new-password"
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
};
