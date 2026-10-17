import { useState } from "react";

import sectionStyles from "../shared/sectionLayout.module.css";
import styles from "./gallery.module.css";

export default function GallerySection({
  title = "Галерея",
  galleryItems = [],
  leftArrowSrc = "/img/left-btn-gallery.png",
  rightArrowSrc = "/img/right-btn-gallery.png",
}) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [activePhotoIndex, setActivePhotoIndex] = useState(0);
  const [imageStatus, setImageStatus] = useState("loading");

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

  const totalPhotos = activeGallery.photos?.length ?? 0;
  const currentPhotoSrc = totalPhotos
    ? activeGallery.photos[activePhotoIndex]
    : null;

  const handleProjectChange = (nextIndex) => {
    setActiveIndex(nextIndex);
    setActivePhotoIndex(0);
    setImageStatus("loading");
  };

  const handlePhotoChange = (direction) => {
    if (!totalPhotos) {
      return;
    }

    setActivePhotoIndex(
      (prev) => (prev + direction + totalPhotos) % totalPhotos,
    );
    setImageStatus("loading");
  };

  return (
    <section className={sectionStyles.section}>
      <div className={sectionStyles.inner}>
        <h2 className={sectionStyles.title}>{title}</h2>
        <div className={styles.gallery}>
          <img
            className={styles.image}
            src={activeGallery.image}
            alt="Gallery main view"
          />
          {galleryItems.map((item, index) => (
            <button
              key={item.label || index}
              className={`${styles.tab} ${
                activeIndex === index ? styles.chosen : ""
              }`}
              style={{ top: `${46 + index * 100}px` }}
              onClick={() => handleProjectChange(index)}
              type="button"
              aria-pressed={activeIndex === index}
            >
              {item.label}
            </button>
          ))}

          <div className={styles.viewer}>
            <div aria-live="polite" className={styles.box}>
              {!totalPhotos ? (
                <p role="status" className={styles.placeholder}>
                  Для этого раздела пока нет фотографий.
                </p>
              ) : (
                <>
                  {imageStatus === "loading" && (
                    <div
                      role="status"
                      className={styles.placeholder}
                      data-testid="loading-placeholder"
                    >
                      Загрузка...
                    </div>
                  )}

                  {imageStatus === "error" && (
                    <div
                      role="status"
                      className={`${styles.placeholder} ${styles.error}`}
                      data-testid="error-placeholder"
                    >
                      Не удалось загрузить изображение
                    </div>
                  )}

                  {imageStatus !== "error" && currentPhotoSrc && (
                    <img
                      key={currentPhotoSrc}
                      className={`${styles.photo} ${
                        imageStatus === "loaded" ? "" : styles.hidden
                      }`}
                      src={currentPhotoSrc}
                      alt={`${activeGallery.label} screenshot ${activePhotoIndex + 1}`}
                      onLoad={() => setImageStatus("loaded")}
                      onError={() => setImageStatus("error")}
                    />
                  )}
                </>
              )}
            </div>

            <div className={styles.pagination}>
              <button
                className={styles.control}
                onClick={() => handlePhotoChange(-1)}
                type="button"
                aria-label="Previous photo"
                disabled={totalPhotos <= 1}
              >
                <img className={styles.arrow} src={leftArrowSrc} alt="" />
              </button>
              <span className={styles.counter}>
                {totalPhotos ? activePhotoIndex + 1 : 0}/{totalPhotos}
              </span>
              <button
                className={styles.control}
                onClick={() => handlePhotoChange(1)}
                type="button"
                aria-label="Next photo"
                disabled={totalPhotos <= 1}
              >
                <img className={styles.arrow} src={rightArrowSrc} alt="" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
