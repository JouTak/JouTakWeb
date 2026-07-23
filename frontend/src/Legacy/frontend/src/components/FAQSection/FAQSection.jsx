import PropTypes from "prop-types";

import FAQItem from "./FAQItem.jsx";
import styles from "./FAQSection.module.css";

export default function FAQSection({ title = "FAQ", items = [] }) {
  return (
    <section className={styles.section} aria-labelledby="new-design-faq-title">
      <div className={styles.inner}>
        <h2 id="new-design-faq-title" className={styles.title}>
          {title}
        </h2>
        <div className={styles.items}>
          {items.map((item) => (
            <FAQItem key={item.question} item={item} />
          ))}
        </div>
      </div>
    </section>
  );
}

FAQSection.propTypes = {
  title: PropTypes.string,
  items: PropTypes.arrayOf(
    PropTypes.shape({
      answer: PropTypes.string.isRequired,
      question: PropTypes.string.isRequired,
    }),
  ),
};
