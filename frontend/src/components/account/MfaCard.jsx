import PropTypes from "prop-types";
import { Button, Label } from "@gravity-ui/uikit";

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

export default function MfaCard({ profile }) {
  const has2fa = profile?.has_2fa === true;

  function openMfaSetup() {
    window.location.href = "/accounts/mfa/";
  }

  return (
    <section style={cardStyle}>
      <div style={headerStyle}>
        <h3 style={{ margin: 0, fontSize: 18 }}>
          Двухфакторная аутентификация (TOTP)
        </h3>
        {has2fa ? (
          <Label theme="success" size="m">
            Включена
          </Label>
        ) : (
          <Label theme="normal" size="m">
            Выключена
          </Label>
        )}
      </div>

      <div style={{ opacity: 0.8 }}>
        Используйте приложение-аутентификатор (Google Authenticator, 1Password и
        т.п.) для генерации одноразовых кодов.
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Button view="normal" onClick={openMfaSetup}>
          {has2fa ? "Управлять 2FA" : "Включить 2FA"}
        </Button>
      </div>
    </section>
  );
}

MfaCard.propTypes = {
  profile: PropTypes.shape({
    has_2fa: PropTypes.bool,
  }),
};

MfaCard.defaultProps = {
  profile: null,
};
