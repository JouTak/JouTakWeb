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
                    <button onClick={handleOpen} className={isOpen ? styles.openBtn : styles.closeBtn}>
                        {!isOpen ? <img src="img/close-qa-btn.png" alt="" /> : <img src="img/open-qa-btn.png" alt="" />}
                    </button>
                    <h3 className={styles.question}>{question}</h3>
                </div>
                {isOpen && <p className={styles.answer}>{answer}</p>}
            </div>
        )
}