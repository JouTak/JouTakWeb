import clsx from "clsx";
import { Link } from "react-router-dom";

import ResponsiveMedia from "../../media/ResponsiveMedia";
import styles from "./projectCard.module.css";

export default function ProjectCard({
  title,
  description,
  image,
  imageMedia,
  to,
  extended = false,
  imageHeight,
}) {
  const imageStyle = imageHeight
    ? { height: imageHeight, aspectRatio: "auto" }
    : undefined;

  return (
    <Link
      to={to}
      className={clsx(styles.card, { [styles.extended]: extended })}
    >
      <div className={styles.imageWrapper}>
        {imageMedia ? (
          <ResponsiveMedia
            media={imageMedia}
            alt={title}
            sizes="(max-width: 480px) 100vw, (max-width: 1024px) 50vw, 33vw"
          />
        ) : (
          <img src={image} alt={title} style={imageStyle} loading="lazy" />
        )}
      </div>

      <div className={styles.projectInfo}>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </Link>
  );
}
