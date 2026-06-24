import PropTypes from "prop-types";

import EventCard from "./EventCard.jsx";
import styles from "./EventsSection.module.css";

function normalizeEvent(event, index) {
  if (typeof event === "string") {
    return {
      title: `Событие ${index + 1}`,
      description: event,
    };
  }
  return event;
}

export default function EventsSection({
  title = "События сообщества",
  items = [],
}) {
  return (
    <section className={styles.section} aria-labelledby="events-title-v2">
      <div className={styles.inner}>
        <h2 id="events-title-v2" className={styles["section-title"]}>
          {title}
        </h2>
        <div className={styles.list}>
          {items.map((event, index) => {
            const normalizedEvent = normalizeEvent(event, index);
            return (
              <EventCard
                key={normalizedEvent.id || normalizedEvent.title}
                event={normalizedEvent}
              />
            );
          })}
        </div>
      </div>
    </section>
  );
}

EventsSection.propTypes = {
  title: PropTypes.string,
  items: PropTypes.arrayOf(
    PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.shape({
        date: PropTypes.string,
        description: PropTypes.string.isRequired,
        href: PropTypes.string,
        id: PropTypes.string,
        image: PropTypes.string,
        location: PropTypes.string,
        title: PropTypes.string.isRequired,
        to: PropTypes.string,
      }),
    ]),
  ),
};
