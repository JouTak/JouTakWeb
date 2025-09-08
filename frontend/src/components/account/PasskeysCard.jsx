import { useEffect, useState } from "react";
import { Button, Label, Loader, TextInput } from "@gravity-ui/uikit";
import {
  listAuthenticators,
  registerPasskeyFlow,
  deleteWebAuthnAuthenticators,
  renameWebAuthnAuthenticator,
} from "../../services/api";

const cardStyle = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 12,
  padding: 16,
  display: "grid",
  gap: 12,
};

const row = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 12,
};

export default function PasskeysCard() {
  const [loading, setLoading] = useState(false);
  const [authenticators, setAuthenticators] = useState([]);
  const [msg, setMsg] = useState("");
  const [nameDrafts, setNameDrafts] = useState({});

  async function reload() {
    setLoading(true);
    setMsg("");
    try {
      const list = await listAuthenticators();
      setAuthenticators(list);
    } catch (e) {
      const m =
        e?.message === "headless_not_authenticated"
          ? "Нужно заново подтвердить учётную запись (reauth) или включить бридж."
          : "Не удалось загрузить список аутентификаторов.";
      setMsg(m);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
  }, []);

  async function onAddPasskey() {
    setLoading(true);
    setMsg("");
    try {
      await registerPasskeyFlow("Мой Passkey");
      setMsg("Passkey добавлен.");
      await reload();
    } catch (e) {
      if (e?.name === "NotAllowedError") {
        setMsg("Операция отменена пользователем.");
      } else if (e?.message === "headless_not_authenticated") {
        setMsg(
          "Нужно повторно войти (reauth) или активировать бридж /api/bridge/headless/login.",
        );
      } else if (e?.response?.status === 401) {
        setMsg(
          "Нужно подтвердить действие (reauth). Откройте заново страницу безопасности.",
        );
      } else {
        setMsg(e?.message || "Не удалось создать Passkey.");
      }
    } finally {
      setLoading(false);
    }
  }

  function onlyWebAuthn(list) {
    return (list || []).filter((a) => a?.type === "webauthn");
  }

  async function onDelete(id) {
    setLoading(true);
    setMsg("");
    try {
      await deleteWebAuthnAuthenticators([id]);
      setMsg("Passkey удалён.");
      await reload();
    } catch {
      setMsg("Не удалось удалить Passkey.");
    } finally {
      setLoading(false);
    }
  }

  async function onRename(id) {
    const newName = (nameDrafts[id] || "").trim();
    if (!newName) return;
    setLoading(true);
    setMsg("");
    try {
      await renameWebAuthnAuthenticator(id, newName);
      setMsg("Название обновлено.");
      setNameDrafts((m) => ({ ...m, [id]: "" }));
      await reload();
    } catch {
      setMsg("Не удалось переименовать Passkey.");
    } finally {
      setLoading(false);
    }
  }

  const webauthn = onlyWebAuthn(authenticators);

  return (
    <section style={cardStyle}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <h3 style={{ margin: 0, fontSize: 18 }}>Passkeys</h3>
        {loading && <Loader size="s" />}
      </div>

      <div style={{ opacity: 0.8 }}>
        Passkey — аутентификация без пароля (Face ID/Touch ID/Windows Hello) на
        поддерживаемых устройствах.
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Button view="normal" onClick={onAddPasskey} disabled={loading}>
          Добавить Passkey
        </Button>
      </div>

      {webauthn?.length ? (
        <div style={{ display: "grid", gap: 8 }}>
          {webauthn.map((a) => (
            <div
              key={a.id}
              style={{
                ...row,
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: 10,
                padding: 12,
              }}
            >
              <div style={{ display: "grid", gap: 4 }}>
                <div>
                  <b>{a.name || "Без названия"}</b>{" "}
                  <Label size="s" theme="normal">
                    WebAuthn {a?.is_passwordless ? "· Passkey" : ""}
                  </Label>
                </div>
                <div style={{ opacity: 0.7, fontSize: 12 }}>
                  Создан:{" "}
                  {a.created_at
                    ? new Date(a.created_at * 1000).toLocaleString()
                    : "—"}
                  {a.last_used_at
                    ? ` · Последнее использование: ${new Date(a.last_used_at * 1000).toLocaleString()}`
                    : ""}
                </div>
                <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
                  <TextInput
                    size="m"
                    placeholder="Новое имя"
                    value={nameDrafts[a.id] || ""}
                    onUpdate={(v) =>
                      setNameDrafts((m) => ({ ...m, [a.id]: v }))
                    }
                  />
                  <Button
                    view="outlined"
                    size="m"
                    onClick={() => onRename(a.id)}
                    disabled={!nameDrafts[a.id]}
                  >
                    Переименовать
                  </Button>
                  <Button
                    view="outlined-danger"
                    size="m"
                    onClick={() => onDelete(a.id)}
                  >
                    Удалить
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ opacity: 0.8 }}>Пока нет сохранённых Passkey.</div>
      )}

      {msg && <div style={{ opacity: 0.9 }}>{msg}</div>}
    </section>
  );
}
