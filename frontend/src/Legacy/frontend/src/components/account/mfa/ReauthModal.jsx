import { Button, Modal, TextInput } from "@gravity-ui/uikit";
import PropTypes from "prop-types";

export default function ReauthModal({
  open,
  pending,
  loading,
  error,
  password,
  onPasswordChange,
  code,
  onCodeChange,
  onClose,
  onPasswordSubmit,
  onCodeSubmit,
  onPasskeySubmit,
}) {
  if (!open || !pending) return null;
  const canUsePasskey =
    typeof window !== "undefined" &&
    "PublicKeyCredential" in window &&
    pending.webauthn;

  return (
    <Modal open={open} onClose={onClose}>
      <div style={{ padding: 20, display: "grid", gap: 14, maxWidth: 480 }}>
        <h3 style={{ margin: 0 }}>Подтвердите действие</h3>
        <p style={{ margin: 0, opacity: 0.82 }}>
          Для этой операции сервер требует недавнее подтверждение личности.
        </p>
        {pending.password ? (
          <form
            onSubmit={onPasswordSubmit}
            style={{ display: "grid", gap: 10 }}
          >
            <TextInput
              size="l"
              type="password"
              label="Пароль"
              value={password}
              onUpdate={onPasswordChange}
              autoComplete="current-password"
              disabled={loading}
            />
            <Button view="action" type="submit" loading={loading}>
              Подтвердить паролем
            </Button>
          </form>
        ) : null}
        {pending.mfa ? (
          <form onSubmit={onCodeSubmit} style={{ display: "grid", gap: 10 }}>
            <TextInput
              size="l"
              label="Код аутентификатора"
              value={code}
              onUpdate={onCodeChange}
              autoComplete="one-time-code"
              disabled={loading}
            />
            <Button view="outlined" type="submit" loading={loading}>
              Подтвердить кодом
            </Button>
          </form>
        ) : null}
        {canUsePasskey ? (
          <Button view="outlined" loading={loading} onClick={onPasskeySubmit}>
            Подтвердить через passkey
          </Button>
        ) : null}
        {error ? (
          <div style={{ color: "#ff8e8e", fontSize: 13 }}>{error}</div>
        ) : null}
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <Button view="flat" disabled={loading} onClick={onClose}>
            Отмена
          </Button>
        </div>
      </div>
    </Modal>
  );
}

ReauthModal.propTypes = {
  open: PropTypes.bool.isRequired,
  pending: PropTypes.shape({
    password: PropTypes.bool,
    mfa: PropTypes.bool,
    webauthn: PropTypes.bool,
  }),
  loading: PropTypes.bool.isRequired,
  error: PropTypes.string.isRequired,
  password: PropTypes.string.isRequired,
  onPasswordChange: PropTypes.func.isRequired,
  code: PropTypes.string.isRequired,
  onCodeChange: PropTypes.func.isRequired,
  onClose: PropTypes.func.isRequired,
  onPasswordSubmit: PropTypes.func.isRequired,
  onCodeSubmit: PropTypes.func.isRequired,
  onPasskeySubmit: PropTypes.func.isRequired,
};
