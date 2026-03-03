import { useEffect, useState, useMemo, useCallback } from "react";
import {
  Button,
  Label,
  TextInput,
  useToaster,
  Loader,
} from "@gravity-ui/uikit";
import {
  getEmailStatus,
  changeEmail,
  resendEmailVerification,
} from "../../services/api";

const cardStyle = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 12,
  padding: 16,
  display: "grid",
  gap: 12,
};

const headerStyle = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 12,
};

export default function EmailCard() {
  const [email, setEmail] = useState("");
  const [verified, setVerified] = useState(false);
  const [pendingEmail, setPendingEmail] = useState("");
  const [resendTarget, setResendTarget] = useState("");
  const [loading, setLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const { add } = useToaster();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const s = await getEmailStatus();
      setEmail(s.email || "");
      setVerified(!!s.verified);
      setPendingEmail(s.pending_email || "");
      setResendTarget(s.resend_target || "");
      setNewEmail(s.email || "");
    } catch {
      add({
        name: "email-load-error",
        title: "Ошибка",
        content: "Не удалось загрузить статус email",
        theme: "danger",
      });
    } finally {
      setLoading(false);
    }
  }, [add]);

  useEffect(() => {
    load();
  }, [load]);

  async function onResend() {
    setBusy(true);
    try {
      const { message } = await resendEmailVerification(resendTarget);
      add({
        name: "email-resend",
        title: "Подтверждение",
        content: message || "Письмо отправлено",
        theme: "success",
      });
    } catch (err) {
      const errors = err?.response?.data?.errors;
      const msg =
        (Array.isArray(errors) &&
          errors.find(
            (item) => item && typeof item.message === "string" && item.message.trim(),
          )?.message) ||
        err?.response?.data?.detail ||
        "Не удалось отправить письмо";
      add({
        name: "email-resend-err",
        title: "Ошибка",
        content: String(msg),
        theme: "danger",
      });
    } finally {
      setBusy(false);
    }
  }

  async function onSave(evt) {
    evt.preventDefault();
    if (!newEmail || newEmail === email) {
      setEditMode(false);
      return;
    }
    setBusy(true);
    try {
      const result = await changeEmail(newEmail);
      add({
        name: "email-change",
        title: "Email",
        content: result.message || "Проверьте почту для подтверждения",
        theme: "success",
      });
      setEmail(result.email || email);
      setVerified(!!result.verified);
      setPendingEmail(result.pending_email || String(newEmail || "").trim());
      setResendTarget(
        result.resend_target || result.pending_email || String(newEmail || "").trim(),
      );
      setEditMode(false);
    } catch (err) {
      const errors = err?.response?.data?.errors;
      const msg =
        (Array.isArray(errors) &&
          errors.find(
            (item) => item && typeof item.message === "string" && item.message.trim(),
          )?.message) ||
        err?.response?.data?.detail ||
        "Не удалось изменить email";
      add({
        name: "email-change-err",
        title: "Ошибка",
        content: String(msg),
        theme: "danger",
      });
    } finally {
      setBusy(false);
    }
  }

  function onCancel() {
    setEditMode(false);
    setNewEmail(email || "");
  }

  const canSave = useMemo(
    () => !!newEmail && newEmail !== email,
    [newEmail, email],
  );

  return (
    <section style={cardStyle}>
      <div style={headerStyle}>
        <h3 style={{ margin: 0, fontSize: 18 }}>Email</h3>
        {email ? (
          verified ? (
            <Label theme="success">Подтверждён</Label>
          ) : (
            <Label theme="danger">Не подтверждён</Label>
          )
        ) : null}
      </div>

      {loading ? (
        <Loader size="m" />
      ) : (
        <>
          {!editMode && (
            <>
              <div>
                <b>{email || "—"}</b>
              </div>
              {pendingEmail && (
                <div style={{ opacity: 0.8 }}>
                  Ожидает подтверждения: <b>{pendingEmail}</b>
                </div>
              )}
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Button view="outlined" onClick={() => setEditMode(true)}>
                  Изменить email
                </Button>
                {resendTarget && (
                  <Button view="normal" loading={busy} onClick={onResend}>
                    Отправить письмо повторно
                  </Button>
                )}
              </div>
            </>
          )}

          {editMode && (
            <form onSubmit={onSave} style={{ display: "grid", gap: 12 }}>
              <TextInput
                size="l"
                label="Новый email"
                type="email"
                value={newEmail}
                onUpdate={setNewEmail}
                name="joutak__email"
                autoComplete="email"
                required
              />
              <div
                style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}
              >
                <Button view="flat" onClick={onCancel} disabled={busy}>
                  Отмена
                </Button>
                <Button
                  view="action"
                  type="submit"
                  loading={busy}
                  disabled={!canSave}
                >
                  Сохранить
                </Button>
              </div>
              <div style={{ opacity: 0.75, fontSize: 12 }}>
                После подтверждения новый адрес станет основным для аккаунта.
              </div>
            </form>
          )}
        </>
      )}
    </section>
  );
}
