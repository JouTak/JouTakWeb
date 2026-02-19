import PropTypes from "prop-types";
import { Avatar, Label } from "@gravity-ui/uikit";
import { isPersonalizedProfile } from "../../utils/profileState";

function AccountHero({ profile }) {
  const first = profile?.first_name || "";
  const last = profile?.last_name || "";
  const fullName = [first, last].filter(Boolean).join(" ").trim();
  const displayName =
    fullName || profile?.username || profile?.nickname || "Anonymous";
  const avatarUrl = profile?.avatar_url || "";
  const email = profile?.email || "";
  const isBasicAccount = !isPersonalizedProfile(profile);

  return (
    <section
      style={{
        border: "1px solid rgba(255,255,255,0.12)",
        borderRadius: 12,
        padding: 16,
        display: "grid",
        gridTemplateColumns: "minmax(96px, 120px) 1fr",
        gap: 16,
        alignItems: "center",
      }}
    >
      <div style={{ justifySelf: "center" }}>
        <Avatar
          size="2xl"
          imgUrl={avatarUrl || undefined}
          text={displayName}
          view="outlined"
          title={displayName}
        />
      </div>
      <div style={{ display: "grid", gap: 6 }}>
        <div style={{ fontSize: 22, fontWeight: 700 }}>{displayName}</div>
        {email && (
          <div
            style={{
              opacity: 0.9,
              display: "flex",
              alignItems: "center",
            }}
          >
            <span>
              Email: <b>{email}</b>
            </span>
          </div>
        )}
        {isBasicAccount && (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Label size="s" theme="danger">
              Базовый аккаунт
            </Label>
          </div>
        )}
      </div>
    </section>
  );
}

AccountHero.propTypes = {
  profile: PropTypes.shape({
    first_name: PropTypes.string,
    last_name: PropTypes.string,
    username: PropTypes.string,
    nickname: PropTypes.string,
    avatar_url: PropTypes.string,
    email: PropTypes.string,
    email_verified: PropTypes.bool,
    profile_complete: PropTypes.bool,
    account_active: PropTypes.bool,
    registration_completed: PropTypes.bool,
    profile_tier: PropTypes.string,
    missing_fields: PropTypes.arrayOf(PropTypes.string),
  }),
};

export default AccountHero;
