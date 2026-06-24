import PropTypes from "prop-types";
import { useId, useState } from "react";

import styles from "./FAQSection.module.css";

export default function FAQItem({ item }) {
  const [isOpen, setIsOpen] = useState(false);
  const answerId = useId();

  return (
    <article className={styles.item}>
      <h3 className={styles.question}>
        <button
          type="button"
          className={styles.toggle}
          aria-controls={answerId}
          aria-expanded={isOpen}
          onClick={() => setIsOpen((open) => !open)}
        >
          <span className={styles.icon} aria-hidden="true" />
          <span>{item.question}</span>
        </button>
      </h3>
      <div
        id={answerId}
        className={styles.answerWrapper}
        data-open={isOpen || undefined}
        hidden={!isOpen}
      >
        <p className={styles.answer}>{item.answer}</p>
      </div>
    </article>
  );
}

FAQItem.propTypes = {
  item: PropTypes.shape({
    answer: PropTypes.string.isRequired,
    question: PropTypes.string.isRequired,
  }).isRequired,
};
