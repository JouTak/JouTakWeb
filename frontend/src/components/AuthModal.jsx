import { get as getWebAuthnCredential } from "@github/webauthn-json";
import { Button, Modal, TextInput, useToaster } from "@gravity-ui/uikit";
import PropTypes from "prop-types";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  authenticateMfaCode,
  authenticateWithWebAuthnCredential,
  doLogin,
  doSignupAndLogin,
  finalizeSessionAuthentication,
  getMfaConfig,
  getWebAuthnRequestOptions,
  me,
  requestPasswordReset,
} from "../services/api";
import { markPendingMfaSession } from "../services/auth/tokenStore";
import { extractErrorMessage } from "../services/errors";
import { markPostSignupPersonalizationSession } from "../utils/personalizationNotice";
import { needsPersonalization } from "../utils/profileState";

const fieldBlockStyle = {
  display: "grid",
  gap: 6,
};

const fieldLabelStyle = {
  fontSize: 13,
  lineHeight: 1.25,
  opacity: 0.85,
};

function isSafeInternalPath(path) {
  return (
    typeof path === "string" && path.startsWith("/") && !path.startsWith("//")
  );
}

export default function AuthModal({
  open = false,
  onClose,
  successRedirectTo = null,
}) {
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [busy, setBusy] = useState(false);

  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");

  const [suEmail, setSuEmail] = useState("");
  const [suPassword, setSuPassword] = useState("");
  const [suPassword2, setSuPassword2] = useState("");
  const [resetEmail, setResetEmail] = useState("");
  const [resetError, setResetError] = useState("");
  const [resetSuccess, setResetSuccess] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaError, setMfaError] = useState("");
  const [mfaTypes, setMfaTypes] = useState([]);
  const [passkeyLoginEnabled, setPasskeyLoginEnabled] = useState(false);
  const loginInputRef = useRef(null);
  const signupEmailInputRef = useRef(null);
  const resetEmailInputRef = useRef(null);
  const mfaCodeInputRef = useRef(null);

  const toaster = useToaster();
  const isLogin = mode === "login";
  const isResetPassword = mode === "reset-password";
  const isSignup = mode === "signup";
  const isMfa = mode === "mfa";
  const passkeySupported =
    typeof window !== "undefined" && "PublicKeyCredential" in window;

  const title = useMemo(() => {
    if (isResetPassword) return "Сброс пароля";
    if (isMfa) return "Подтверждение входа";
    if (isLogin) return "Вход";
    return "Регистрация";
  }, [isLogin, isMfa, isResetPassword]);

  const safeSuccessRedirectTo = useMemo(() => {
    if (isSafeInternalPath(successRedirectTo)) return successRedirectTo;
    return null;
  }, [successRedirectTo]);

  function resetForms() {
    setLogin("");
    setPassword("");
    setSuEmail("");
    setSuPassword("");
    setSuPassword2("");
    setResetEmail("");
    setResetError("");
    setResetSuccess("");
    setMfaCode("");
    setMfaError("");
    setMfaTypes([]);
  }

  function close({ notifyParent = true } = {}) {
    markPendingMfaSession(false);
    resetForms();
    setBusy(false);
    if (notifyParent) onClose?.();
  }

  useEffect(() => {
    if (!open) {
      resetForms();
      setMode("login");
      setBusy(false);
      setPasskeyLoginEnabled(false);
    }
  }, [open]);

  useEffect(() => {
    let cancelled = false;
    if (!open || !passkeySupported) {
      setPasskeyLoginEnabled(false);
      return undefined;
    }

    (async () => {
      try {
        const config = await getMfaConfig();
        if (!cancelled) {
          setPasskeyLoginEnabled(config?.passkey_login_enabled === true);
        }
      } catch {
        if (!cancelled) {
          setPasskeyLoginEnabled(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [open, passkeySupported]);

  useEffect(() => {
    if (!open) return undefined;
    const targetControl = isResetPassword
      ? resetEmailInputRef.current
      : isMfa
        ? mfaCodeInputRef.current
        : isLogin
          ? loginInputRef.current
          : isSignup
            ? signupEmailInputRef.current
            : null;
    if (!targetControl) return undefined;

    const frameId = requestAnimationFrame(() => {
      targetControl.focus();
    });

    return () => cancelAnimationFrame(frameId);
  }, [isLogin, isMfa, isResetPassword, isSignup, open]);

  const emailOk = (s) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s);

  function validateLogin() {
    if (!login.trim()) return "Укажите email или старый логин.";
    if (!password) return "Введите пароль.";
    return null;
  }

  function validateSignup() {
    if (!suEmail.trim()) return "Укажите email.";
    if (!emailOk(suEmail)) return "Неверный формат email.";
    if (!suPassword) return "Введите пароль.";
    if (suPassword.length < 8) return "Минимальная длина пароля — 8 символов.";
    if (suPassword2 !== suPassword) return "Пароли не совпадают.";
    return null;
  }

  async function completeAuthenticatedFlow(successMessage) {
    await finalizeSessionAuthentication();
    const profile = await me();
    toaster.add({
      title: "Готово!",
      content: successMessage,
      theme: "success",
    });
    if (needsPersonalization(profile)) {
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
      const result = await doLogin({ login, password });
      if (result?.status === "pending_mfa") {
        setMfaTypes(Array.isArray(result?.types) ? result.types : []);
        setMfaCode("");
        setMfaError("");
        setMode("mfa");
        return;
      }
      await completeAuthenticatedFlow("Вы вошли в аккаунт.");
    } catch (ex) {
      toaster.add({
        title: extractErrorMessage(ex, "Ошибка входа"),
        theme: "danger",
      });
    } finally {
      setBusy(false);
    }
  }

  async function onPasskeyLogin() {
    setBusy(true);
    try {
      const options = await getWebAuthnRequestOptions("login");
      const credential = await getWebAuthnCredential({ publicKey: options });
      await authenticateWithWebAuthnCredential("login", credential);
      await completeAuthenticatedFlow("Вы вошли с помощью passkey.");
    } catch (ex) {
      toaster.add({
        title: extractErrorMessage(ex, "Не удалось войти через passkey."),
        theme: "danger",
      });
      setBusy(false);
    }
  }

  async function onMfaSubmit(e) {
    e.preventDefault();
    if (!mfaCode.trim()) {
      setMfaError(
        "Введите код из приложения-аутентификатора или recovery code.",
      );
      return;
    }

    setBusy(true);
    setMfaError("");
    try {
      await authenticateMfaCode(mfaCode);
      await completeAuthenticatedFlow("Вход подтверждён.");
    } catch (ex) {
      const message = extractErrorMessage(
        ex,
        "Не удалось подтвердить второй фактор.",
      );
      setMfaError(message);
      toaster.add({
        title: message,
        theme: "danger",
      });
    } finally {
      setBusy(false);
    }
  }

  async function onMfaPasskeyLogin() {
    setBusy(true);
    setMfaError("");
    try {
      const options = await getWebAuthnRequestOptions("authenticate");
      const credential = await getWebAuthnCredential({ publicKey: options });
      await authenticateWithWebAuthnCredential("authenticate", credential);
      await completeAuthenticatedFlow("Вход подтверждён через passkey.");
    } catch (ex) {
      const message = extractErrorMessage(
        ex,
        "Не удалось подтвердить вход через passkey.",
      );
      setMfaError(message);
      toaster.add({
        title: message,
        theme: "danger",
      });
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
        email: suEmail.trim(),
        password: suPassword,
      });
      toaster.add({
        title: "Аккаунт создан",
        content: "Аккаунт создан. Теперь можно продолжить настройку профиля.",
        theme: "success",
      });
      const profile = await me();
      if (needsPersonalization(profile)) {
        markPostSignupPersonalizationSession(profile);
        close({ notifyParent: !safeSuccessRedirectTo });
        navigate("/account/complete-registration", { replace: true });
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
            <div style={fieldBlockStyle}>
              <span style={fieldLabelStyle}>Email или старый логин</span>
              <TextInput
                size="l"
                value={login}
                onUpdate={setLogin}
                name="joutak__login"
                autoComplete="username"
                controlRef={loginInputRef}
                disabled={busy}
                aria-label="Email или старый логин"
              />
            </div>
            <div style={fieldBlockStyle}>
              <span style={fieldLabelStyle}>Пароль</span>
              <TextInput
                size="l"
                type="password"
                value={password}
                onUpdate={setPassword}
                name="joutak__password"
                autoComplete="current-password"
                disabled={busy}
                aria-label="Пароль"
              />
            </div>
            <Button
              view="action"
              size="l"
              loading={busy}
              width="max"
              type="submit"
            >
              Войти
            </Button>

            {passkeySupported && passkeyLoginEnabled ? (
              <Button
                view="outlined"
                size="l"
                width="max"
                type="button"
                loading={busy}
                onClick={onPasskeyLogin}
              >
                Войти с помощью passkey
              </Button>
            ) : null}

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
        ) : isMfa ? (
          <form onSubmit={onMfaSubmit} style={{ display: "grid", gap: 12 }}>
            <p style={{ margin: 0, opacity: 0.9 }}>
              Пароль принят. Подтвердите вход кодом из
              приложения-аутентификатора, recovery code
              {mfaTypes.includes("webauthn") ? " или passkey" : ""}.
            </p>

            <div style={fieldBlockStyle}>
              <span style={fieldLabelStyle}>Код подтверждения</span>
              <TextInput
                size="l"
                value={mfaCode}
                onUpdate={setMfaCode}
                name="joutak__mfa_code"
                autoComplete="one-time-code"
                controlRef={mfaCodeInputRef}
                disabled={busy}
                aria-label="Код подтверждения"
              />
            </div>

            {mfaError ? (
              <p style={{ margin: 0, color: "#ff8e8e" }}>{mfaError}</p>
            ) : null}

            <Button
              view="action"
              size="l"
              loading={busy}
              width="max"
              type="submit"
            >
              Подтвердить вход
            </Button>

            {passkeySupported && mfaTypes.includes("webauthn") ? (
              <Button
                view="outlined"
                size="l"
                width="max"
                type="button"
                loading={busy}
                onClick={onMfaPasskeyLogin}
              >
                Использовать passkey
              </Button>
            ) : null}

            <Button
              view="flat"
              size="l"
              width="max"
              type="button"
              disabled={busy}
              onClick={() => {
                setMode("login");
                setMfaCode("");
                setMfaError("");
              }}
            >
              Назад ко входу
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
                <div style={fieldBlockStyle}>
                  <span style={fieldLabelStyle}>Email</span>
                  <TextInput
                    size="l"
                    type="email"
                    value={resetEmail}
                    onUpdate={setResetEmail}
                    autoComplete="email"
                    controlRef={resetEmailInputRef}
                    disabled={busy}
                    aria-label="Email"
                  />
                </div>
                {resetError ? (
                  <p style={{ margin: 0, color: "#ff8e8e" }}>{resetError}</p>
                ) : null}
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
            <div style={fieldBlockStyle}>
              <span style={fieldLabelStyle}>Email</span>
              <TextInput
                size="l"
                type="email"
                value={suEmail}
                onUpdate={setSuEmail}
                name="joutak__email"
                autoComplete="email"
                controlRef={signupEmailInputRef}
                disabled={busy}
                aria-label="Email"
              />
            </div>
            <div style={fieldBlockStyle}>
              <span style={fieldLabelStyle}>Пароль</span>
              <TextInput
                size="l"
                type="password"
                value={suPassword}
                onUpdate={setSuPassword}
                name="joutak__password"
                autoComplete="new-password"
                disabled={busy}
                aria-label="Пароль"
              />
            </div>
            <div style={fieldBlockStyle}>
              <span style={fieldLabelStyle}>Повторите пароль</span>
              <TextInput
                size="l"
                type="password"
                value={suPassword2}
                onUpdate={setSuPassword2}
                name="joutak__password"
                autoComplete="new-password"
                disabled={busy}
                aria-label="Повторите пароль"
              />
            </div>
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
