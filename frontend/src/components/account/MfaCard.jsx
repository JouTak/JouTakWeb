import {
  create as createWebAuthnCredential,
  get as getWebAuthnCredential,
} from "@github/webauthn-json";
import { Label, Loader, useToaster } from "@gravity-ui/uikit";
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
import { SectionCard } from "../ui/primitives";
import PasskeysSection from "./mfa/PasskeysSection";
import ReauthModal from "./mfa/ReauthModal";
import RecoveryCodesSection from "./mfa/RecoveryCodesSection";
import { rowBetweenStyle, warningBoxStyle } from "./mfa/shared";
import TotpSection from "./mfa/TotpSection";

// ─── Safe API wrappers (treat 404 as "not configured") ─────────────────────

const EMPTY_TOTP = {
  enabled: false,
  authenticator: null,
  recovery_codes_generated: false,
  secret: "",
  totp_url: "",
};

async function getTotpSafe() {
  try {
    return await getTotpStatus();
  } catch (error) {
    if (error?.response?.status === 404) return EMPTY_TOTP;
    throw error;
  }
}

async function getMfaConfigSafe() {
  try {
    return await getMfaConfig();
  } catch (error) {
    if (error?.response?.status === 404) {
      return { supported_types: [], passkey_login_enabled: false };
    }
    throw error;
  }
}

async function listAuthenticatorsSafe() {
  try {
    return await listAuthenticators();
  } catch (error) {
    if (error?.response?.status === 404) return [];
    throw error;
  }
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

// ─── MfaCard (orchestrator) ────────────────────────────────────────────────

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
  const [totpSetupActive, setTotpSetupActive] = useState(false);
  const [totpProvisioning, setTotpProvisioning] = useState(false);

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

  // ── Initial load ──────────────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [nextConfig, nextAuthenticators, nextTotp] = await Promise.all([
          getMfaConfigSafe(),
          listAuthenticatorsSafe(),
          getTotpSafe(),
        ]);
        if (cancelled) return;
        setConfig(nextConfig);
        setAuthenticators(nextAuthenticators);
        setTotpStatus(nextTotp);
      } catch (error) {
        if (!cancelled) {
          if (isUnverifiedEmailError(error)) {
            setConfig({ supported_types: [], passkey_login_enabled: false });
            setAuthenticators([]);
            setTotpStatus({
              ...EMPTY_TOTP,
              blocked_by_email_verification: true,
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
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [add]);

  // ── QR code generation ────────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false;
    if (totpStatus?.enabled || !totpStatus?.totp_url) {
      setQrDataUrl("");
      return undefined;
    }
    QRCode.toDataURL(totpStatus.totp_url, {
      margin: 0,
      width: 200,
      color: { dark: "#f4f7fb", light: "#0000" },
    })
      .then((value) => {
        if (!cancelled) setQrDataUrl(value);
      })
      .catch(() => {
        if (!cancelled) setQrDataUrl("");
      });
    return () => {
      cancelled = true;
    };
  }, [totpStatus]);

  // ── Shared helpers ────────────────────────────────────────────────────

  async function refreshState() {
    const [nextAuthenticators, nextTotp] = await Promise.all([
      listAuthenticatorsSafe(),
      getTotpSafe(),
    ]);
    setAuthenticators(nextAuthenticators);
    setTotpStatus(nextTotp);
  }

  function openReauth(error, retry) {
    const pending = extractReauthFlows(error);
    if (!pending.password && !pending.mfa) throw error;
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
      if (!reauthState) setBusyKey("");
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
      if (retry) await retry();
    } catch (error) {
      setReauthError(
        extractErrorMessage(error, "Не удалось подтвердить действие."),
      );
    } finally {
      setBusyKey("");
    }
  }

  // ── TOTP handlers ─────────────────────────────────────────────────────

  async function handleStartTotpSetup() {
    setTotpProvisioning(true);
    try {
      let totp = await getTotpSafe();
      if (!totp.totp_url) totp = await getTotpSafe();
      setTotpStatus(totp);
      setTotpSetupActive(true);
    } catch (error) {
      add({
        name: "mfa-totp-provision-error",
        title: "Ошибка",
        content: extractErrorMessage(
          error,
          "Не удалось подготовить аутентификатор.",
        ),
        theme: "danger",
      });
    } finally {
      setTotpProvisioning(false);
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
      setTotpSetupActive(false);
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
      setTotpSetupActive(false);
      await refreshState();
      add({
        name: "mfa-totp-deactivated",
        title: "Аутентификатор отключён",
        content: "Вход через приложение-аутентификатор больше не используется.",
        theme: "success",
      });
    });
  }

  // ── Recovery codes handler ────────────────────────────────────────────

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

  // ── Passkey handlers ──────────────────────────────────────────────────

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

  // ── Derived state ─────────────────────────────────────────────────────

  const emailVerified = profile?.email_verified !== false;
  const mfaBlocked =
    !emailVerified || totpStatus?.blocked_by_email_verification === true;

  // ── Render ────────────────────────────────────────────────────────────

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
          <div style={warningBoxStyle}>
            <strong>Email не подтверждён</strong>
            <div style={{ opacity: 0.84 }}>
              Сначала подтвердите email, затем можно включить двухфакторную
              защиту.
            </div>
          </div>
        ) : null}

        <TotpSection
          totpStatus={totpStatus}
          totpSetupActive={totpSetupActive}
          totpProvisioning={totpProvisioning}
          totpCode={totpCode}
          qrDataUrl={qrDataUrl}
          busyKey={busyKey}
          mfaBlocked={mfaBlocked}
          onTotpCodeChange={setTotpCode}
          onStartSetup={handleStartTotpSetup}
          onCancelSetup={() => {
            setTotpSetupActive(false);
            setTotpCode("");
          }}
          onActivate={handleActivateTotp}
          onDeactivate={handleDeactivateTotp}
        />

        <RecoveryCodesSection
          recoverySummary={recoverySummary}
          recoveryCodes={recoveryCodes}
          expanded={recoveryExpanded}
          busyKey={busyKey}
          mfaBlocked={mfaBlocked}
          onExpand={() => setRecoveryExpanded(true)}
          onCollapse={() => {
            setRecoveryExpanded(false);
            setRecoveryCodes([]);
          }}
          onRegenerate={handleRegenerateRecoveryCodes}
        />

        <PasskeysSection
          webauthnAuthenticators={webauthnAuthenticators}
          expanded={passkeysExpanded}
          newPasskeyName={newPasskeyName}
          renamingId={renamingId}
          renamingName={renamingName}
          busyKey={busyKey}
          deleteTarget={deleteTarget}
          mfaBlocked={mfaBlocked}
          onExpand={() => setPasskeysExpanded(true)}
          onCollapse={() => setPasskeysExpanded(false)}
          onNewNameChange={setNewPasskeyName}
          onAdd={handleAddPasskey}
          onStartRename={(auth) => {
            setRenamingId(auth.id);
            setRenamingName(auth.name || "");
          }}
          onRenamingNameChange={setRenamingName}
          onConfirmRename={handleRenamePasskey}
          onCancelRename={() => {
            setRenamingId(null);
            setRenamingName("");
          }}
          onRequestDelete={setDeleteTarget}
          onConfirmDelete={handleDeletePasskey}
          onCancelDelete={() => setDeleteTarget(null)}
        />
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
    </>
  );
}

MfaCard.propTypes = {
  profile: PropTypes.shape({
    has_2fa: PropTypes.bool,
    email_verified: PropTypes.bool,
  }),
};
