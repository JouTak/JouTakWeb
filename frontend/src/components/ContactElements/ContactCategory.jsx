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
