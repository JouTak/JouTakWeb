import EventCard from './EventCard'
import styles from './eventCard.module.css'
import sectionStyles from '../shared/sectionLayout.module.css'
import events from './events.data.js'

export default function EventsSection() {
    return (
        <section className={sectionStyles.section}>
            <div className={sectionStyles.inner}>
                <div className={styles.eventsList}>
                    {events.map(event => (
                        <EventCard key={event.title} {...event}/>
                    ))}
                </div>
            </div>
        </section>
    )
}