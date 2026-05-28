import { useState } from 'react'
import sectionStyles from '../shared/sectionLayout.module.css'
import styles from './gallery.module.css'

export default function GallerySection({
    title = 'Галерея',
    galleryItems = [],
    leftArrowSrc = '/img/left-btn-gallery.png',
    rightArrowSrc = '/img/right-btn-gallery.png',
}) {
    const [activeIndex, setActiveIndex] = useState(0)
    const [activePhotoIndex, setActivePhotoIndex] = useState(0)
    const activeGallery = galleryItems[activeIndex] ?? galleryItems[0]

    if (!activeGallery) {
        return null
    }

    const totalPhotos = activeGallery.photos.length

    const handleProjectChange = (nextIndex) => {
        setActiveIndex(nextIndex)
        setActivePhotoIndex(0)
    }

    const handlePhotoChange = (direction) => {
        if (!totalPhotos) {
            return
        }

        setActivePhotoIndex((prev) => (prev + direction + totalPhotos) % totalPhotos)
    }

    return (
        <section className={sectionStyles.section}>
            <div className={sectionStyles.inner}>
                <h2 className={sectionStyles.title}>{title}</h2>
                <div className={styles.gallery}>
                    <img className={styles.galleryImage} src={activeGallery.image} alt="Gallery main view" />
                    {galleryItems.map((item, index) => (
                        <button
                            key={item.label}
                            className={`${styles.galleryButton} ${
                                activeIndex === index ? styles.chosenButton : ''
                            }`}
                            style={{ top: `${46 + index * 100}px` }}
                            onClick={() => handleProjectChange(index)}
                            type="button"
                        >
                            {item.label}
                        </button>
                    ))}
                    <div className={styles.photoViewer}>
                        <img
                            className={styles.photoViewerImage}
                            src={activeGallery.photos[activePhotoIndex]}
                            alt={`${activeGallery.label} screenshot ${activePhotoIndex + 1}`}
                        />
                        <div className={styles.galleryPagination}>
                            <button
                                className={styles.paginationButton}
                                onClick={() => handlePhotoChange(-1)}
                                type="button"
                                aria-label="Previous photo"
                            >
                                <img className={styles.paginationArrow} src={leftArrowSrc} alt="" />
                            </button>
                            <span className={styles.paginationCounter}>
                                {activePhotoIndex + 1}/{totalPhotos}
                            </span>
                            <button
                                className={styles.paginationButton}
                                onClick={() => handlePhotoChange(1)}
                                type="button"
                                aria-label="Next photo"
                            >
                                <img className={styles.paginationArrow} src={rightArrowSrc} alt="" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    )
}       