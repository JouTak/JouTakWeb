import { FiCalendar } from "react-icons/fi";
import { GrLocation } from "react-icons/gr";

import ResponsiveMedia from "../../media/ResponsiveMedia";
import MinecraftButton from "../MinecraftButton/MinecraftButton";
import styles from "./eventCard.module.css";

export default function EventCard({
  title,
  description,
  location,
  image,
  imageMedia,
  date,
  to,
  imageWidth,
  alt = "Описание картинки",
}) {
  const formattedDate = new Date(date).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  });

  const eventImageStyle = imageWidth
    ? { width: imageWidth, maxWidth: imageWidth, flex: `0 0 ${imageWidth}` }
    : undefined;

  return (
    <div className={styles.card}>
      <div className={styles.text}>
        <h3 className={styles.title}>{title}</h3>
        <p className={styles.info}>
          <FiCalendar /> {formattedDate || "Скоро"}
        </p>
        <p className={styles.info}>
          <GrLocation /> {location}
        </p>
        <p className={styles.description}>{description}</p>
        <MinecraftButton
          onClick={() => {
            if (to) window.location.assign(to);
          }}
        >
          регистрация
        </MinecraftButton>
      </div>
      {imageMedia ? (
        <ResponsiveMedia
          media={imageMedia}
          alt={alt}
          className={styles.eventImg}
          pictureClassName={styles.eventMedia}
          sizes="(max-width: 768px) 100vw, 50vw"
        />
      ) : (
        <img
          className={styles.eventImg}
          src={image}
          width="739"
          style={eventImageStyle}
          alt={alt}
          loading="lazy"
        />
      )}
    </div>
  );
}
