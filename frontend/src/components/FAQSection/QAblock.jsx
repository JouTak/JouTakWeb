import React from "react";

import styles from "./faq.module.css";

export default function QAblock({ question, answer }) {
  const [isOpen, setIsOpen] = React.useState(false);
  const answerID = React.useId();
  function handleOpen() {
    setIsOpen((prev) => !prev);
  }

  return (
    <div className={styles.qaBlock}>
      <div className={styles.qaHead}>
        <button
          onClick={handleOpen}
          className={`${styles.toggleBtn} ${isOpen ? styles.toggleBtnOpen : ""}`}
          aria-expanded={isOpen}
          aria-controls={answerID}
          aria-label={question}
          type="button"
        >
          <img src="img/close-qa-btn.png" alt="" />
        </button>
        <h3 className={styles.question}>{question}</h3>
      </div>
      <div
        id={answerID}
        className={`${styles.answerWrapper} ${isOpen ? styles.answerWrapperOpen : ""}`}
        hidden={!isOpen}
      >
        <p className={styles.answer}>{answer}</p>
      </div>
    </div>
  );
}
