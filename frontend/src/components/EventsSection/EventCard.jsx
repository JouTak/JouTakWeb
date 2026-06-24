import PropTypes from "prop-types";

import styles from "./EventsSection.module.css";

function formatDate(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "long",
  }).format(date);
}

export default function EventCard({ event }) {
  const date = formatDate(event.date);
  const href = event.href || event.to;

  return (
    <article className={styles.card}>
      <div className={styles.content}>
        <h3 className={styles.title}>{event.title}</h3>
        {(date || event.location) && (
          <div className={styles.meta}>
            {date && <span>{date}</span>}
            {event.location && <span>{event.location}</span>}
          </div>
        )}
        <p className={styles.description}>{event.description}</p>
        {href && (
          <a className={styles.action} href={href}>
            Регистрация
          </a>
        )}
      </div>
      {event.image && (
        <img className={styles.image} src={event.image} alt="" loading="lazy" />
      )}
    </article>
  );
}

EventCard.propTypes = {
  event: PropTypes.shape({
    date: PropTypes.string,
    description: PropTypes.string.isRequired,
    href: PropTypes.string,
    image: PropTypes.string,
    location: PropTypes.string,
    to: PropTypes.string,
    title: PropTypes.string.isRequired,
  }).isRequired,
};
