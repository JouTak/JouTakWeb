import ContactButton from "./ContactButton";
import styles from "./ContactElements.module.scss";

export default function ContactCategory({ title, contactsData }) {
  console.log(styles);
  return (
    <div className={styles.contactCategory}>
      <h6>{title}</h6>
      <div className={styles.contactCategoryContent}>
        {contactsData?.map((contactInfo, index) => (
          <ContactButton key={index} {...contactInfo} />
        ))}
      </div>
    </div>
  );
}
