import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, TextInput, useToaster } from "@gravity-ui/uikit";
import {
  clearAuthState,
  deleteCurrentAccount,
} from "../../services/api";

const cardStyle = {
  border: "1px solid rgba(255,120,120,0.35)",
  borderRadius: 12,
  padding: 16,
  display: "grid",
  gap: 12,
  background: "rgba(255,80,80,0.08)",
};

export default function DeleteAccountCard() {
  const navigate = useNavigate();
  const { add } = useToaster();

  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmText, setConfirmText] = useState("");

  const canSubmit = useMemo(
    () => password.length > 0 && confirmText.trim() === "УДАЛИТЬ",
    [confirmText, password.length],
  );

  async function onDelete(event) {
    event.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    try {
      const data = await deleteCurrentAccount(password);
      clearAuthState();
      add({
        name: "account-delete-success",
        title: "Аккаунт удалён",
        content: data?.message || "Ваш аккаунт был удалён",
        theme: "success",
      });
      navigate("/joutak", { replace: true });
    } catch (err) {
      const message = err?.response?.data?.detail || "Не удалось удалить аккаунт";
      add({
        name: "account-delete-error",
        title: "Ошибка",
        content: String(message),
        theme: "danger",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section style={cardStyle}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12,
        }}
      >
        <h3 style={{ margin: 0, fontSize: 18 }}>Удаление аккаунта</h3>
        {!open && (
          <Button view="outlined" onClick={() => setOpen(true)}>
            Удалить аккаунт
          </Button>
        )}
      </div>

      <div style={{ opacity: 0.9 }}>
        Вы можете запросить удаление аккаунта. При удалении ваш профиль пропадает из системы,
      </div>

      {open && (
        <form onSubmit={onDelete} style={{ display: "grid", gap: 12 }}>
          <div style={{ fontSize: 13, opacity: 0.9 }}>
            Удаление необратимо. Для подтверждения введи пароль и слово
            <b> УДАЛИТЬ</b>.
          </div>

          <TextInput
            size="l"
            type="password"
            label="Текущий пароль"
            value={password}
            onUpdate={setPassword}
            autoComplete="current-password"
            required
          />

          <TextInput
            size="l"
            label='Введите "УДАЛИТЬ"'
            value={confirmText}
            onUpdate={setConfirmText}
            required
          />

          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: 8,
            }}
          >
            <Button
              view="flat"
              type="button"
              onClick={() => {
                setOpen(false);
                setPassword("");
                setConfirmText("");
              }}
              disabled={busy}
            >
              Отмена
            </Button>
            <Button
              view="outlined"
              type="submit"
              loading={busy}
              disabled={!canSubmit}
            >
              Подтвердить удаление
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}
