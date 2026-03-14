import EventCard from './EventCard'
import styles from './eventCard.module.css'
import events from './events.data.js'

export default function EventsSection() {
    return (
        <section className={styles.eventsSection}>
            {events.map(event => (
                <EventCard key={event.title} {...event}/>
            ))}
        </section>
    )
}