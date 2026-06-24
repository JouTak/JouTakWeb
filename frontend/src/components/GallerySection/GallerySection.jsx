import PropTypes from "prop-types";
import { useState } from "react";

import styles from "./GallerySection.module.css";

export default function GallerySection({ title = "Галерея", items = [] }) {
  const [activeIndex, setActiveIndex] = useState(0);

  if (items.length === 0) return null;

  const normalizedIndex = activeIndex % items.length;
  const activeItem = items[normalizedIndex];
  const source = typeof activeItem === "string" ? activeItem : activeItem.src;
  const alt =
    typeof activeItem === "string"
      ? `JouTak gallery ${normalizedIndex + 1}`
      : activeItem.alt || `JouTak gallery ${normalizedIndex + 1}`;

  function changePhoto(direction) {
    setActiveIndex((index) => (index + direction + items.length) % items.length);
  }

  return (
    <section className={styles.section} aria-labelledby="gallery-title-v2">
      <div className={styles.inner}>
        <h2 id="gallery-title-v2" className={styles.title}>
          {title}
        </h2>
        <div className={styles.viewer}>
          <img className={styles.image} src={source} alt={alt} />
          <div className={styles.controls}>
            <button
              type="button"
              className={styles.button}
              aria-label="Предыдущее фото"
              onClick={() => changePhoto(-1)}
            >
              ←
            </button>
            <span className={styles.counter} aria-live="polite">
              {normalizedIndex + 1}/{items.length}
            </span>
            <button
              type="button"
              className={styles.button}
              aria-label="Следующее фото"
              onClick={() => changePhoto(1)}
            >
              →
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

GallerySection.propTypes = {
  title: PropTypes.string,
  items: PropTypes.arrayOf(
    PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.shape({
        alt: PropTypes.string,
        src: PropTypes.string.isRequired,
      }),
    ]),
  ),
};
