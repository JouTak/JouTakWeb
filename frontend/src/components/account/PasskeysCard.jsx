import { Button, Label } from "@gravity-ui/uikit";

import { SectionCard } from "../ui/primitives";

export default function PasskeysCard() {
  function openMfaSettings() {
    window.location.href = "/accounts/mfa/";
  }

  return (
    <SectionCard>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <h3 style={{ margin: 0, fontSize: 18 }}>Passkeys</h3>
        <Label size="s" theme="warning">
          Не подключено
        </Label>
      </div>

      <div style={{ opacity: 0.8 }}>
        Управление Passkeys оставлено выключенным, пока для него нет
        поддерживаемого frontend API-клиента.
      </div>

      <div>
        <Button view="normal" onClick={openMfaSettings}>
          Открыть настройки MFA
        </Button>
      </div>
    </SectionCard>
  );
}
