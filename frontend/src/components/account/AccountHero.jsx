import { Avatar, Label } from "@gravity-ui/uikit";
import PropTypes from "prop-types";

import { getProfileDisplayName } from "../../utils/accountIdentity";
import { isPersonalizedProfile } from "../../utils/profileState";
import { SectionCard } from "../ui/primitives.jsx";
import styles from "./AccountHero.module.css";

function AccountHero({ profile }) {
  const displayName = getProfileDisplayName(profile);
  const avatarUrl = profile?.avatar_url || "";
  const email = profile?.email || "";
  const isBasicAccount = !isPersonalizedProfile(profile);

  return (
    <SectionCard className={styles.hero}>
      <div className={styles.avatar}>
        <Avatar
          size="2xl"
          imgUrl={avatarUrl || undefined}
          text={displayName}
          view="outlined"
          title={displayName}
        />
      </div>
      <div className={styles.details}>
        <div className={styles.name}>{displayName}</div>
        {email && (
          <div className={styles.email}>
            <span>
              Email: <b>{email}</b>
            </span>
          </div>
        )}
        {isBasicAccount && (
          <div className={styles.labels}>
            <Label size="s" theme="danger">
              Базовый аккаунт
            </Label>
          </div>
        )}
      </div>
    </SectionCard>
  );
}

AccountHero.propTypes = {
  profile: PropTypes.shape({
    first_name: PropTypes.string,
    last_name: PropTypes.string,
    username: PropTypes.string,
    minecraft_nick: PropTypes.string,
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
