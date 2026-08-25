import PropTypes from "prop-types";

import styles from "./ContactElements.module.scss";

export default function ContactButton({ link, iconPath, label }) {
  return (
    <a className={styles.contactButton} href={link}>
      <div className={styles.contactButtonInner}>
        <span>
          <img src={iconPath} alt={[label, "ico"].join("-")} />
        </span>
        <span>{label}</span>
      </div>
    </a>
  );
}

ContactButton.propTypes = {
  link: PropTypes.string.isRequired,
  iconPath: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
};
