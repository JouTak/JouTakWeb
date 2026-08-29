import PropTypes from "prop-types";
import { useState } from "react";

import { getMediaDescriptor } from "../../media/mediaResolver";
import sectionStyles from "../shared/sectionLayout.module.css";
import styles from "./gallery.module.css";

function mediaDescriptor(media) {
  if (typeof media === "string") {
    return { src: media, sources: [] };
  }
  return getMediaDescriptor(media);
}

function GalleryMedia({ media, alt, className }) {
  const descriptor = mediaDescriptor(media);

  if (descriptor?.designPlaceholder) {
    return (
      <div
        className={`${className} ${styles.designPlaceholder}`}
        data-design-placeholder={descriptor.designPlaceholder}
        role="status"
      >
        <span>Скриншот готовится</span>
        <small>Здесь появится игровой кадр после передачи ассета.</small>
      </div>
    );
  }

  if (!descriptor?.src) {
    return null;
  }

  return (
    <img className={className} src={descriptor.src} alt={alt} loading="lazy" />
  );
}

GalleryMedia.propTypes = {
  media: PropTypes.oneOfType([PropTypes.string, PropTypes.object]),
  alt: PropTypes.string.isRequired,
  className: PropTypes.string.isRequired,
};

export default function GallerySection({
  title = "Галерея",
  galleryItems = [],
  leftArrowSrc = "/img/left-btn-gallery.png",
  rightArrowSrc = "/img/right-btn-gallery.png",
}) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [activePhotoIndex, setActivePhotoIndex] = useState(0);
  const activeGallery = galleryItems[activeIndex] ?? galleryItems[0];

  if (!activeGallery) {
    return (
      <section className={sectionStyles.section}>
        <div className={sectionStyles.inner}>
          <h2 className={sectionStyles.title}>{title}</h2>
          <p role="status">Фотографии пока не добавлены.</p>
        </div>
      </section>
    );
  }

  const totalPhotos = activeGallery.photos.length;

  const handleProjectChange = (nextIndex) => {
    setActiveIndex(nextIndex);
    setActivePhotoIndex(0);
  };

  const handlePhotoChange = (direction) => {
    if (!totalPhotos) {
      return;
    }

    setActivePhotoIndex(
      (prev) => (prev + direction + totalPhotos) % totalPhotos,
    );
  };

  return (
    <section className={sectionStyles.section}>
      <div className={sectionStyles.inner}>
        <h2 className={sectionStyles.title}>{title}</h2>
        <div className={styles.gallery}>
          <GalleryMedia
            className={styles.galleryImage}
            media={activeGallery.image}
            alt="Gallery main view"
          />
          {galleryItems.map((item, index) => (
            <button
              key={item.label}
              className={`${styles.galleryButton} ${
                activeIndex === index ? styles.chosenButton : ""
              }`}
              style={{ top: `${46 + index * 100}px` }}
              onClick={() => handleProjectChange(index)}
              type="button"
              aria-pressed={activeIndex === index}
            >
              {item.label}
            </button>
          ))}
          <div className={styles.photoViewer}>
            <div aria-live="polite">
              {totalPhotos ? (
                <GalleryMedia
                  className={styles.photoViewerImage}
                  media={activeGallery.photos[activePhotoIndex]}
                  alt={`${activeGallery.label} screenshot ${activePhotoIndex + 1}`}
                />
              ) : (
                <p role="status">Для этого раздела пока нет фотографий.</p>
              )}
            </div>
            <div className={styles.galleryPagination}>
              <button
                className={styles.paginationButton}
                onClick={() => handlePhotoChange(-1)}
                type="button"
                aria-label="Previous photo"
                disabled={totalPhotos <= 1}
              >
                <img
                  className={styles.paginationArrow}
                  src={leftArrowSrc}
                  alt=""
                />
              </button>
              <span className={styles.paginationCounter}>
                {totalPhotos ? activePhotoIndex + 1 : 0}/{totalPhotos}
              </span>
              <button
                className={styles.paginationButton}
                onClick={() => handlePhotoChange(1)}
                type="button"
                aria-label="Next photo"
                disabled={totalPhotos <= 1}
              >
                <img
                  className={styles.paginationArrow}
                  src={rightArrowSrc}
                  alt=""
                />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
