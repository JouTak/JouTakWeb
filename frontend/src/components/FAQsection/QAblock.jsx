import styles from './faq.module.css'
import React from 'react'

export default function QAblock({
                                question,
                                answer
                                }) 
{
        const [isOpen, setIsOpen] = React.useState(false)

        function handleOpen() {
            setIsOpen(prev => !prev)
        }

        return (
            <div className={styles.qaBlock}>
                <div className={styles.qaHead}>
                    <button
                        onClick={handleOpen}
                        className={`${styles.toggleBtn} ${isOpen ? styles.toggleBtnOpen : ''}`}
                        aria-expanded={isOpen}
                    >
                        <img src="img/close-qa-btn.png" alt="" />
                    </button>
                    <h3 className={styles.question}>{question}</h3>
                </div>
                <div className={`${styles.answerWrapper} ${isOpen ? styles.answerWrapperOpen : ''}`}>
                    <p className={styles.answer}>{answer}</p>
                </div>
            </div>
        )
}