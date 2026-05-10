import {
  create as createWebAuthnCredential,
  get as getWebAuthnCredential,
} from "@github/webauthn-json";
import {
  Button,
  Label,
  Loader,
  Modal,
  TextInput,
  useToaster,
} from "@gravity-ui/uikit";
import PropTypes from "prop-types";
import QRCode from "qrcode";
import { useEffect, useMemo, useState } from "react";

import {
  activateTotp,
  addWebAuthnCredential,
  authenticateWithWebAuthnCredential,
  deactivateTotp,
  deleteWebAuthnCredentials,
  getMfaConfig,
  getTotpStatus,
  getWebAuthnRegistrationOptions,
  getWebAuthnRequestOptions,
  listAuthenticators,
  reauthenticateWithMfaCode,
  reauthenticateWithPassword as reauthWithPassword,
  regenerateRecoveryCodes,
  renameWebAuthnCredential,
} from "../../services/api";
import { extractErrorMessage } from "../../services/errors";
import { ConfirmDialog, SectionCard } from "../ui/primitives";

const rowBetweenStyle = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 12,
  flexWrap: "wrap",
};

const blockStyle = {
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 8,
  padding: 14,
  display: "grid",
  gap: 12,
};

function formatTimestamp(value) {
  if (!value) return "Никогда";
  const date = new Date(Number(value) * 1000);
  if (Number.isNaN(date.getTime())) return "Никогда";
  return date.toLocaleString("ru-RU");
}

function extractReauthFlows(error) {
  const flows = Array.isArray(error?.response?.data?.data?.flows)
    ? error.response.data.data.flows
    : [];
  return {
    password: flows.some((flow) => flow?.id === "reauthenticate"),
    mfa: flows.some((flow) => flow?.id === "mfa_reauthenticate"),
    webauthn: flows.some(
      (flow) =>
        flow?.id === "mfa_reauthenticate" &&
        Array.isArray(flow?.types) &&
        flow.types.includes("webauthn"),
    ),
  };
}

function isUnverifiedEmailError(error) {
  return (
    error?.response?.status === 409 &&
    error?.response?.data?.error_code === "unverified_email"
  );
}

function ActionBlock({ title, children, badge = null }) {
  return (
    <div style={blockStyle}>
      <div style={rowBetweenStyle}>
        <h4 style={{ margin: 0, fontSize: 16 }}>{title}</h4>
        {badge}
      </div>
      {children}
    </div>
  );
}

ActionBlock.propTypes = {
  title: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired,
  badge: PropTypes.node,
};

function ReauthModal({
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

export default function MfaCard({ profile = null }) {
  const { add } = useToaster();
  const [loading, setLoading] = useState(true);
  const [config, setConfig] = useState({
    supported_types: [],
    passkey_login_enabled: false,
  });
  const [authenticators, setAuthenticators] = useState([]);
  const [totpStatus, setTotpStatus] = useState(null);
  const [totpCode, setTotpCode] = useState("");
  const [qrDataUrl, setQrDataUrl] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState([]);
  const [newPasskeyName, setNewPasskeyName] = useState("Основной ключ");
  const [renamingId, setRenamingId] = useState(null);
  const [renamingName, setRenamingName] = useState("");
  const [busyKey, setBusyKey] = useState("");
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [reauthState, setReauthState] = useState(null);
  const [reauthPassword, setReauthPassword] = useState("");
  const [reauthCode, setReauthCode] = useState("");
  const [reauthError, setReauthError] = useState("");
  const [recoveryExpanded, setRecoveryExpanded] = useState(false);
  const [passkeysExpanded, setPasskeysExpanded] = useState(false);

  const webauthnAuthenticators = useMemo(
    () => authenticators.filter((auth) => auth.type === "webauthn"),
    [authenticators],
  );
  const recoverySummary = useMemo(
    () => authenticators.find((auth) => auth.type === "recovery_codes") || null,
    [authenticators],
  );
  const hasMfa =
    profile?.has_2fa === true ||
    authenticators.some(
      (auth) => auth.type === "totp" || auth.type === "webauthn",
    );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [nextConfig, nextAuthenticators, nextTotp] = await Promise.all([
          getMfaConfig(),
          listAuthenticators(),
          getTotpStatus(),
        ]);
        if (cancelled) return;
        setConfig(nextConfig);
        setAuthenticators(nextAuthenticators);
        setTotpStatus(nextTotp);
      } catch (error) {
        if (!cancelled) {
          if (isUnverifiedEmailError(error)) {
            setConfig({
              supported_types: [],
              passkey_login_enabled: false,
            });
            setAuthenticators([]);
            setTotpStatus({
              enabled: false,
              authenticator: null,
              recovery_codes_generated: false,
              blocked_by_email_verification: true,
              secret: "",
              totp_url: "",
            });
            setLoading(false);
            return;
          }
          add({
            name: "mfa-load-error",
            title: "Ошибка",
            content: extractErrorMessage(error, "Не удалось загрузить MFA."),
            theme: "danger",
          });
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [add]);

  useEffect(() => {
    let cancelled = false;
    if (totpStatus?.enabled || !totpStatus?.totp_url) {
      setQrDataUrl("");
      return undefined;
    }
    QRCode.toDataURL(totpStatus.totp_url, {
      margin: 0,
      width: 200,
      color: {
        dark: "#f4f7fb",
        light: "#0000",
      },
    })
      .then((value) => {
        if (!cancelled) {
          setQrDataUrl(value);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setQrDataUrl("");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [totpStatus]);

  async function refreshState() {
    const [nextAuthenticators, nextTotp] = await Promise.all([
      listAuthenticators(),
      getTotpStatus(),
    ]);
    setAuthenticators(nextAuthenticators);
    setTotpStatus(nextTotp);
  }

  function openReauth(error, retry) {
    const pending = extractReauthFlows(error);
    if (!pending.password && !pending.mfa) {
      throw error;
    }
    setReauthState({ pending, retry });
    setReauthPassword("");
    setReauthCode("");
    setReauthError("");
  }

  async function runProtectedAction(key, action) {
    setBusyKey(key);
    try {
      await action();
    } catch (error) {
      if (error?.response?.status === 401) {
        openReauth(error, async () => {
          setBusyKey(key);
          try {
            await action();
          } finally {
            setBusyKey("");
          }
        });
        return;
      }
      add({
        name: `mfa-action-error-${key}`,
        title: "Ошибка",
        content: extractErrorMessage(error, "Не удалось выполнить действие."),
        theme: "danger",
      });
    } finally {
      if (!reauthState) {
        setBusyKey("");
      }
    }
  }

  async function handleReauthRetry(work) {
    setBusyKey("reauth");
    try {
      await work();
      const retry = reauthState?.retry;
      setReauthState(null);
      setReauthPassword("");
      setReauthCode("");
      setReauthError("");
      if (retry) {
        await retry();
      }
    } catch (error) {
      setReauthError(
        extractErrorMessage(error, "Не удалось подтвердить действие."),
      );
    } finally {
      setBusyKey("");
    }
  }

  async function handleActivateTotp() {
    if (!totpCode.trim()) {
      add({
        name: "mfa-totp-code-required",
        title: "Код обязателен",
        content: "Введите код из приложения-аутентификатора.",
        theme: "warning",
      });
      return;
    }
    await runProtectedAction("activate-totp", async () => {
      const result = await activateTotp(totpCode);
      setTotpCode("");
      await refreshState();
      add({
        name: "mfa-totp-activated",
        title: "Защита включена",
        content: result?.recovery_codes_generated
          ? "Аутентификатор подключён. Резервные коды созданы — сохраните их."
          : "Аутентификатор подключён.",
        theme: "success",
      });
    });
  }

  async function handleDeactivateTotp() {
    await runProtectedAction("deactivate-totp", async () => {
      await deactivateTotp();
      setRecoveryCodes([]);
      await refreshState();
      add({
        name: "mfa-totp-deactivated",
        title: "Аутентификатор отключён",
        content: "Вход через приложение-аутентификатор больше не используется.",
        theme: "success",
      });
    });
  }

  async function handleRegenerateRecoveryCodes() {
    await runProtectedAction("regenerate-recovery", async () => {
      const data = await regenerateRecoveryCodes();
      setRecoveryCodes(data?.unused_codes || []);
      await refreshState();
      add({
        name: "mfa-recovery-regenerated",
        title: "Резервные коды обновлены",
        content: "Предыдущие коды аннулированы. Сохраните новые.",
        theme: "success",
      });
    });
  }

  async function handleAddPasskey() {
    await runProtectedAction("add-passkey", async () => {
      const options = await getWebAuthnRegistrationOptions({
        passwordless: config?.passkey_login_enabled === true,
      });
      const credential = await createWebAuthnCredential({ publicKey: options });
      const result = await addWebAuthnCredential({
        name: newPasskeyName,
        credential,
      });
      await refreshState();
      setNewPasskeyName("Резервный ключ");
      add({
        name: "mfa-passkey-added",
        title: "Ключ безопасности добавлен",
        content: result?.recovery_codes_generated
          ? "Ключ создан. Резервные коды сгенерированы — сохраните их."
          : "Ключ создан.",
        theme: "success",
      });
    });
  }

  async function handleRenamePasskey(id) {
    if (!renamingName.trim()) return;
    await runProtectedAction(`rename-passkey-${id}`, async () => {
      await renameWebAuthnCredential(id, renamingName);
      await refreshState();
      setRenamingId(null);
      setRenamingName("");
      add({
        name: "mfa-passkey-renamed",
        title: "Название обновлено",
        content: "Ключ безопасности переименован.",
        theme: "success",
      });
    });
  }

  async function handleDeletePasskey() {
    if (!deleteTarget) return;
    await runProtectedAction(`delete-passkey-${deleteTarget.id}`, async () => {
      await deleteWebAuthnCredentials([deleteTarget.id]);
      setDeleteTarget(null);
      await refreshState();
      add({
        name: "mfa-passkey-deleted",
        title: "Ключ безопасности удалён",
        content: "Ключ больше не может использоваться для входа.",
        theme: "success",
      });
    });
  }

  const emailVerified = profile?.email_verified !== false;
  const mfaBlockedByUnverifiedEmail =
    !emailVerified || totpStatus?.blocked_by_email_verification === true;

  if (loading) {
    return (
      <SectionCard id="mfa">
        <div style={rowBetweenStyle}>
          <h3 style={{ margin: 0, fontSize: 18 }}>Многофакторная защита</h3>
          <Loader size="m" />
        </div>
      </SectionCard>
    );
  }

  return (
    <>
      <SectionCard id="mfa">
        <div style={rowBetweenStyle}>
          <h3 style={{ margin: 0, fontSize: 18 }}>Многофакторная защита</h3>
          <Label theme={hasMfa ? "success" : "normal"} size="m">
            {hasMfa ? "Включена" : "Выключена"}
          </Label>
        </div>

        <div style={{ opacity: 0.84 }}>
          Двухфакторная аутентификация добавляет дополнительный уровень защиты
          при входе в аккаунт. Поддерживаются приложения-аутентификаторы,
          резервные коды и ключи безопасности.
        </div>

        {!emailVerified ? (
          <div
            style={{
              border: "1px solid rgba(255, 163, 0, 0.45)",
              borderRadius: 8,
              padding: 12,
              background: "rgba(255, 163, 0, 0.12)",
              display: "grid",
              gap: 8,
            }}
          >
            <strong>Email не подтверждён</strong>
            <div style={{ opacity: 0.84 }}>
              Сначала подтвердите email, затем можно включить двухфакторную
              защиту.
            </div>
          </div>
        ) : null}

        {/* ── Приложение-аутентификатор (TOTP) ── always visible ── */}
        <ActionBlock
          title="Приложение-аутентификатор"
          badge={
            totpStatus?.enabled ? <Label theme="success">Активен</Label> : null
          }
        >
          {mfaBlockedByUnverifiedEmail ? (
            <div style={{ opacity: 0.84 }}>
              Двухфакторная защита недоступна, пока email не подтверждён.
            </div>
          ) : totpStatus?.enabled ? (
            <>
              <div style={{ opacity: 0.84 }}>
                Последнее использование:{" "}
                {formatTimestamp(totpStatus.authenticator?.last_used_at)}
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Button
                  view="outlined"
                  loading={busyKey === "deactivate-totp"}
                  onClick={handleDeactivateTotp}
                >
                  Отключить аутентификатор
                </Button>
              </div>
            </>
          ) : (
            <>
              <div style={{ opacity: 0.84 }}>
                Откройте приложение (Google Authenticator, Яндекс Ключ или
                аналог), отсканируйте QR-код и введите полученный код.
              </div>
              {qrDataUrl ? (
                <img
                  src={qrDataUrl}
                  alt="TOTP QR"
                  style={{ width: 200, height: 200, borderRadius: 8 }}
                />
              ) : null}
              {totpStatus?.secret ? (
                <div
                  style={{
                    fontFamily: "monospace",
                    wordBreak: "break-all",
                    opacity: 0.92,
                  }}
                >
                  {totpStatus.secret}
                </div>
              ) : null}
              <div style={{ display: "grid", gap: 10, maxWidth: 360 }}>
                <TextInput
                  size="l"
                  label="Код из приложения"
                  value={totpCode}
                  onUpdate={setTotpCode}
                  autoComplete="one-time-code"
                />
                <Button
                  view="action"
                  loading={busyKey === "activate-totp"}
                  onClick={handleActivateTotp}
                  disabled={mfaBlockedByUnverifiedEmail}
                >
                  Подключить аутентификатор
                </Button>
              </div>
            </>
          )}
        </ActionBlock>

        {/* ── Резервные коды ── collapsible ── */}
        <ActionBlock
          title="Резервные коды"
          badge={
            recoverySummary ? (
              <Label theme="info">
                Осталось {recoverySummary.unused_code_count} из{" "}
                {recoverySummary.total_code_count}
              </Label>
            ) : null
          }
        >
          {recoveryExpanded ? (
            <>
              {recoveryCodes.length ? (
                <>
                  <div
                    style={{
                      border: "1px solid rgba(255, 163, 0, 0.45)",
                      borderRadius: 8,
                      padding: 12,
                      background: "rgba(255, 163, 0, 0.12)",
                      display: "grid",
                      gap: 8,
                    }}
                  >
                    <strong>Сохраните коды в безопасное место</strong>
                    <div style={{ opacity: 0.84 }}>
                      Коды показываются только сейчас. После закрытия этого
                      раздела просмотреть их снова будет невозможно.
                    </div>
                  </div>
                  <div
                    style={{
                      display: "grid",
                      gap: 6,
                      fontFamily: "monospace",
                      fontSize: 14,
                    }}
                  >
                    {recoveryCodes.map((code) => (
                      <div key={code}>{code}</div>
                    ))}
                  </div>
                </>
              ) : (
                <div style={{ opacity: 0.84 }}>
                  Одноразовые коды для входа, если приложение-аутентификатор или
                  ключ недоступны.
                </div>
              )}
              {recoverySummary ? (
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <Button
                    view="outlined"
                    loading={busyKey === "regenerate-recovery"}
                    onClick={handleRegenerateRecoveryCodes}
                    disabled={mfaBlockedByUnverifiedEmail}
                  >
                    Сгенерировать новые коды
                  </Button>
                  <Button
                    view="flat"
                    onClick={() => {
                      setRecoveryExpanded(false);
                      setRecoveryCodes([]);
                    }}
                  >
                    Свернуть
                  </Button>
                </div>
              ) : (
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <div style={{ opacity: 0.84 }}>
                    Резервные коды создаются автоматически после подключения
                    аутентификатора или ключа безопасности.
                  </div>
                  <Button
                    view="flat"
                    onClick={() => setRecoveryExpanded(false)}
                  >
                    Свернуть
                  </Button>
                </div>
              )}
            </>
          ) : (
            <div style={rowBetweenStyle}>
              <div style={{ opacity: 0.84 }}>
                Одноразовые коды для входа, если основное устройство недоступно.
              </div>
              <Button view="outlined" onClick={() => setRecoveryExpanded(true)}>
                Управление
              </Button>
            </div>
          )}
        </ActionBlock>

        {/* ── Ключи безопасности (Passkeys) ── collapsible ── */}
        <ActionBlock
          title="Ключи безопасности"
          badge={
            webauthnAuthenticators.length ? (
              <Label theme="success">{webauthnAuthenticators.length} шт.</Label>
            ) : null
          }
        >
          {passkeysExpanded ? (
            <>
              <div style={{ opacity: 0.84 }}>
                Аппаратные ключи или биометрия устройства для быстрого и
                безопасного входа.
              </div>
              <div style={{ display: "grid", gap: 10, maxWidth: 420 }}>
                <TextInput
                  size="l"
                  label="Название нового ключа"
                  value={newPasskeyName}
                  onUpdate={setNewPasskeyName}
                />
                <Button
                  view="action"
                  loading={busyKey === "add-passkey"}
                  onClick={handleAddPasskey}
                  disabled={mfaBlockedByUnverifiedEmail}
                >
                  Добавить ключ безопасности
                </Button>
              </div>
              {webauthnAuthenticators.length ? (
                <div style={{ display: "grid", gap: 10 }}>
                  {webauthnAuthenticators.map((auth) => (
                    <div key={auth.id} style={blockStyle}>
                      <div style={rowBetweenStyle}>
                        <div style={{ display: "grid", gap: 6 }}>
                          <div
                            style={{
                              display: "flex",
                              gap: 8,
                              flexWrap: "wrap",
                            }}
                          >
                            <strong>{auth.name || `Ключ ${auth.id}`}</strong>
                            {auth.is_passwordless ? (
                              <Label theme="success">Passkey</Label>
                            ) : null}
                          </div>
                          <div style={{ opacity: 0.76, fontSize: 13 }}>
                            Последнее использование:{" "}
                            {formatTimestamp(auth.last_used_at)}
                          </div>
                        </div>
                        <div
                          style={{
                            display: "flex",
                            gap: 8,
                            flexWrap: "wrap",
                          }}
                        >
                          <Button
                            view="outlined"
                            onClick={() => {
                              setRenamingId(auth.id);
                              setRenamingName(auth.name || "");
                            }}
                            disabled={mfaBlockedByUnverifiedEmail}
                          >
                            Переименовать
                          </Button>
                          <Button
                            view="flat"
                            onClick={() => setDeleteTarget(auth)}
                            disabled={mfaBlockedByUnverifiedEmail}
                          >
                            Удалить
                          </Button>
                        </div>
                      </div>
                      {renamingId === auth.id ? (
                        <div
                          style={{
                            display: "grid",
                            gap: 8,
                            maxWidth: 360,
                          }}
                        >
                          <TextInput
                            size="l"
                            value={renamingName}
                            onUpdate={setRenamingName}
                          />
                          <div
                            style={{
                              display: "flex",
                              gap: 8,
                              flexWrap: "wrap",
                            }}
                          >
                            <Button
                              view="action"
                              loading={busyKey === `rename-passkey-${auth.id}`}
                              onClick={() => handleRenamePasskey(auth.id)}
                              disabled={mfaBlockedByUnverifiedEmail}
                            >
                              Сохранить
                            </Button>
                            <Button
                              view="flat"
                              onClick={() => {
                                setRenamingId(null);
                                setRenamingName("");
                              }}
                            >
                              Отмена
                            </Button>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : null}
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <Button view="flat" onClick={() => setPasskeysExpanded(false)}>
                  Свернуть
                </Button>
              </div>
            </>
          ) : (
            <div style={rowBetweenStyle}>
              <div style={{ opacity: 0.84 }}>
                Аппаратные ключи или биометрия для входа без ввода кода.
              </div>
              <Button view="outlined" onClick={() => setPasskeysExpanded(true)}>
                Управление
              </Button>
            </div>
          )}
        </ActionBlock>
      </SectionCard>

      <ReauthModal
        open={Boolean(reauthState)}
        pending={reauthState?.pending || null}
        loading={busyKey === "reauth"}
        error={reauthError}
        password={reauthPassword}
        onPasswordChange={setReauthPassword}
        code={reauthCode}
        onCodeChange={setReauthCode}
        onClose={() => {
          setReauthState(null);
          setReauthPassword("");
          setReauthCode("");
          setReauthError("");
        }}
        onPasswordSubmit={(event) => {
          event.preventDefault();
          handleReauthRetry(() => reauthWithPassword(reauthPassword));
        }}
        onCodeSubmit={(event) => {
          event.preventDefault();
          handleReauthRetry(() => reauthenticateWithMfaCode(reauthCode));
        }}
        onPasskeySubmit={() =>
          handleReauthRetry(async () => {
            const options = await getWebAuthnRequestOptions("reauthenticate");
            const credential = await getWebAuthnCredential({
              publicKey: options,
            });
            await authenticateWithWebAuthnCredential(
              "reauthenticate",
              credential,
            );
          })
        }
      />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Удалить ключ безопасности?"
        confirmText="Удалить"
        cancelText="Отмена"
        loading={busyKey === `delete-passkey-${deleteTarget?.id}`}
        onConfirm={handleDeletePasskey}
        onCancel={() => setDeleteTarget(null)}
      >
        {deleteTarget ? (
          <div>
            Ключ <strong>{deleteTarget.name || deleteTarget.id}</strong> больше
            нельзя будет использовать для подтверждения входа.
          </div>
        ) : (
          <div />
        )}
      </ConfirmDialog>
    </>
  );
}

MfaCard.propTypes = {
  profile: PropTypes.shape({
    has_2fa: PropTypes.bool,
  }),
};
