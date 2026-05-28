import QAblock from './QAblock'
import styles from './faq.module.css'
import sectionStyles from '../shared/sectionLayout.module.css'

export default function FAQsection({
    title = 'FAQ',
    faqItems = [],
}) {
    return (
        <section className={sectionStyles.section}>
            <div className={sectionStyles.inner}>
                <h2 className={`${sectionStyles.title} ${styles.title}`}>{title}</h2>
                {faqItems.map(element => (
                    <QAblock key={element.question} {...element}/>
                ))}
            </div>
        </section>
    )
}