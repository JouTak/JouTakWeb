import PropTypes from "prop-types";

import ContactButton from "./ContactButton";
import styles from "./ContactElements.module.scss";

export default function ContactCategory({ title, contactsData }) {
  return (
    <div className={styles.contactCategory}>
      <h2 className={styles.contactCategoryTitle}>{title}</h2>
      <div className={styles.contactCategoryContent}>
        {contactsData?.map((contactInfo, index) => (
          <ContactButton key={index} {...contactInfo} />
        ))}
      </div>
    </div>
  );
}

ContactCategory.propTypes = {
  title: PropTypes.string.isRequired,
  contactsData: PropTypes.arrayOf(
    PropTypes.shape({
      link: PropTypes.string.isRequired,
      iconPath: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
    }),
  ),
};
