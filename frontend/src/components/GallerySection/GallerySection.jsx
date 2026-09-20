import PropTypes from "prop-types";
import { useState } from "react";

import { getMediaDescriptor } from "../../media/mediaResolver";
import sectionStyles from "../shared/sectionLayout.module.css";
import styles from "./gallery.module.css";

function mediaDescriptor(media) {
  if (typeof media === "string") {
    return { src: media.trim() === "#" ? "" : media.trim(), sources: [] };
  }
  return getMediaDescriptor(media);
}

function GalleryMedia({ media, alt, className }) {
  const descriptor = mediaDescriptor(media);
  const [failedSource, setFailedSource] = useState(null);

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

  if (!descriptor?.src || failedSource === descriptor.src) {
    return (
      <div className={`${className} ${styles.designPlaceholder}`} role="status">
        <span>Фото недоступно</span>
        <small>Попробуй выбрать другой кадр.</small>
      </div>
    );
  }

  return (
    <img
      className={className}
      src={descriptor.src}
      srcSet={
        descriptor.sources
          .map((source) => `${source.src} ${source.width}w`)
          .join(", ") || undefined
      }
      sizes="(max-width: 760px) 100vw, (max-width: 1520px) 70vw, 1100px"
      alt={media?.alt || alt}
      loading="lazy"
      onError={() => setFailedSource(descriptor.src)}
    />
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

  const photos = activeGallery.photos.filter((photo) => {
    const descriptor = mediaDescriptor(photo);
    return (
      descriptor?.designPlaceholder ||
      (descriptor?.src && descriptor.src !== "#")
    );
  });
  const totalPhotos = photos.length;
  const photoIndex = Math.min(activePhotoIndex, Math.max(0, totalPhotos - 1));

  const handleProjectChange = (nextIndex) => {
    setActiveIndex(nextIndex);
    setActivePhotoIndex(0);
  };

  const handlePhotoChange = (direction) => {
    if (!totalPhotos) {
      return;
    }

    setActivePhotoIndex((photoIndex + direction + totalPhotos) % totalPhotos);
  };

  return (
    <section className={sectionStyles.section}>
      <div className={sectionStyles.inner}>
        <h2 className={sectionStyles.title}>{title}</h2>
        <div className={styles.gallery}>
          <div
            className={styles.galleryTabs}
            role="group"
            aria-label="Разделы галереи"
          >
            {galleryItems.map((item, index) => (
              <button
                key={item.label}
                className={`${styles.galleryButton} ${
                  activeIndex === index ? styles.chosenButton : ""
                }`}
                onClick={() => handleProjectChange(index)}
                type="button"
                aria-pressed={activeIndex === index}
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className={styles.photoViewer}>
            <div aria-live="polite">
              {totalPhotos ? (
                <GalleryMedia
                  className={styles.photoViewerImage}
                  media={photos[photoIndex]}
                  alt={`${activeGallery.label} screenshot ${photoIndex + 1}`}
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
                {totalPhotos ? photoIndex + 1 : 0}/{totalPhotos}
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
