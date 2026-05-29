import { Button, Label, TextInput } from "@gravity-ui/uikit";
import PropTypes from "prop-types";

import { blockStyle, formatTimestamp, rowBetweenStyle } from "./shared";

export default function TotpSection({
  totpStatus,
  totpSetupActive,
  totpProvisioning,
  totpCode,
  qrDataUrl,
  busyKey,
  mfaBlocked,
  onTotpCodeChange,
  onStartSetup,
  onCancelSetup,
  onActivate,
  onDeactivate,
}) {
  return (
    <div style={blockStyle}>
      <div style={rowBetweenStyle}>
        <h4 style={{ margin: 0, fontSize: 16 }}>Приложение-аутентификатор</h4>
        {totpStatus?.enabled ? <Label theme="success">Активен</Label> : null}
      </div>

      {mfaBlocked ? (
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
              onClick={onDeactivate}
            >
              Отключить аутентификатор
            </Button>
          </div>
        </>
      ) : totpSetupActive && totpStatus?.totp_url ? (
        <>
          <div style={{ opacity: 0.84 }}>
            Откройте приложение (Google Authenticator, Яндекс Ключ или аналог),
            отсканируйте QR-код и введите полученный код.
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
              onUpdate={onTotpCodeChange}
              autoComplete="one-time-code"
            />
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <Button
                view="action"
                loading={busyKey === "activate-totp"}
                onClick={onActivate}
                disabled={mfaBlocked}
              >
                Подключить аутентификатор
              </Button>
              <Button view="flat" onClick={onCancelSetup}>
                Отмена
              </Button>
            </div>
          </div>
        </>
      ) : (
        <div style={rowBetweenStyle}>
          <div style={{ opacity: 0.84 }}>
            Одноразовые коды из приложения для подтверждения входа.
          </div>
          <Button
            view="action"
            loading={totpProvisioning}
            onClick={onStartSetup}
            disabled={mfaBlocked}
          >
            Настроить
          </Button>
        </div>
      )}
    </div>
  );
}

TotpSection.propTypes = {
  totpStatus: PropTypes.object,
  totpSetupActive: PropTypes.bool.isRequired,
  totpProvisioning: PropTypes.bool.isRequired,
  totpCode: PropTypes.string.isRequired,
  qrDataUrl: PropTypes.string.isRequired,
  busyKey: PropTypes.string.isRequired,
  mfaBlocked: PropTypes.bool.isRequired,
  onTotpCodeChange: PropTypes.func.isRequired,
  onStartSetup: PropTypes.func.isRequired,
  onCancelSetup: PropTypes.func.isRequired,
  onActivate: PropTypes.func.isRequired,
  onDeactivate: PropTypes.func.isRequired,
};
