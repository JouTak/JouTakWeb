import QAblock from './QAblock'
import styles from './faq.module.css'
import sectionStyles from '../shared/sectionLayout.module.css'
import faq from './faq.data.js'

export default function FAQsection() {
    return (
        <section className={sectionStyles.section}>
            <div className={sectionStyles.inner}>
                <h2 className={`${sectionStyles.title} ${styles.title}`}>FAQ</h2>
                {faq.map(element => (
                    <QAblock key={element.question} {...element}/>
                ))}
            </div>
        </section>
    )
}