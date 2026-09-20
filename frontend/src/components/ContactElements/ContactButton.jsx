import PropTypes from "prop-types";

import styles from "./ContactElements.module.scss";

export default function ContactButton({ link, iconPath, label }) {
  return (
    <a
      target="_blank"
      className={styles.contactButton}
      href={link}
      rel="noreferrer"
    >
      <span>
        <img src={iconPath} alt={[label, "ico"].join(" ")} />
      </span>
      <span>{label}</span>
    </a>
  );
}

ContactButton.propTypes = {
  link: PropTypes.string.isRequired,
  iconPath: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
};
