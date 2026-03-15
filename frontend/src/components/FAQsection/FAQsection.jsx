import QAblock from './QAblock'
import styles from './faq.module.css'
import faq from './faq.data.js'

export default function FAQsection() {
    return (
        <section className={styles.faqSection}>
            <div className={styles.inner}>
                <h2 className={styles.title}>FAQ</h2>
                {faq.map(element => (
                    <QAblock key={element.question} {...element}/>
                ))}
            </div>
        </section>
    )
}