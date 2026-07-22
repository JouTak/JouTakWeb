import { Button, Label } from "@gravity-ui/uikit";
import PropTypes from "prop-types";

import { blockStyle, rowBetweenStyle, warningBoxStyle } from "./shared";

export default function RecoveryCodesSection({
  recoverySummary,
  recoveryCodes,
  expanded,
  busyKey,
  mfaBlocked,
  onExpand,
  onCollapse,
  onRegenerate,
}) {
  return (
    <div style={blockStyle}>
      <div style={rowBetweenStyle}>
        <h4 style={{ margin: 0, fontSize: 16 }}>Резервные коды</h4>
        {recoverySummary ? (
          <Label theme="info">
            Осталось {recoverySummary.unused_code_count} из{" "}
            {recoverySummary.total_code_count}
          </Label>
        ) : null}
      </div>

      {expanded ? (
        <>
          {recoveryCodes.length ? (
            <>
              <div style={warningBoxStyle}>
                <strong>Сохраните коды в безопасное место</strong>
                <div style={{ opacity: 0.84 }}>
                  Коды показываются только сейчас. После закрытия этого раздела
                  просмотреть их снова будет невозможно.
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
                onClick={onRegenerate}
                disabled={mfaBlocked}
              >
                Сгенерировать новые коды
              </Button>
              <Button view="flat" onClick={onCollapse}>
                Свернуть
              </Button>
            </div>
          ) : (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <div style={{ opacity: 0.84 }}>
                Резервные коды создаются автоматически после подключения
                аутентификатора или ключа безопасности.
              </div>
              <Button view="flat" onClick={onCollapse}>
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
          <Button view="outlined" onClick={onExpand}>
            Управление
          </Button>
        </div>
      )}
    </div>
  );
}

RecoveryCodesSection.propTypes = {
  recoverySummary: PropTypes.object,
  recoveryCodes: PropTypes.arrayOf(PropTypes.string).isRequired,
  expanded: PropTypes.bool.isRequired,
  busyKey: PropTypes.string.isRequired,
  mfaBlocked: PropTypes.bool.isRequired,
  onExpand: PropTypes.func.isRequired,
  onCollapse: PropTypes.func.isRequired,
  onRegenerate: PropTypes.func.isRequired,
};
