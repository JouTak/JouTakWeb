import { useState } from 'react'
import sectionStyles from '../shared/sectionLayout.module.css'
import styles from './gallery.module.css'

export default function GallerySection() {
    const galleryItems = [
        {
            label: 'JouTak SMP',
            image: '/img/gallery-bg.png',
            buttonClass: styles.buttonOne,
            photos: ['/img/joutak.png', '/img/бункер.png', '/img/gallery-example-photo.png'],
        },
        {
            label: 'ITMOcraft',
            image: '/img/gallery-bg-2.png',
            buttonClass: styles.buttonTwo,
            photos: ['/img/itmocraft.png', '/img/minigames.png', '/img/gallery-example-photo.png'],
        },
        {
            label: 'MiniGames',
            image: '/img/gallery-bg-3.png',
            buttonClass: styles.buttonThree,
            photos: ['/img/minigames.png', '/img/бункер.png', '/img/gallery-example-photo.png'],
        },
        {
            label: 'Legacy',
            image: '/img/gallery-bg-4.png',
            buttonClass: styles.buttonFour,
            photos: ['/img/legacy.png', '/img/бункер.png', '/img/gallery-example-photo.png'],
        },
    ]

    const [activeIndex, setActiveIndex] = useState(0)
    const [activePhotoIndex, setActivePhotoIndex] = useState(0)
    const activeGallery = galleryItems[activeIndex]
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
                <h2 className={sectionStyles.title}>Галерея проектов</h2>
                <div className={styles.gallery}>
                    <img className={styles.galleryImage} src={activeGallery.image} alt="Gallery main view" />
                    {galleryItems.map((item, index) => (
                        <button
                            key={item.label}
                            className={`${styles.galleryButton} ${item.buttonClass} ${
                                activeIndex === index ? styles.chosenButton : ''
                            }`}
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
                                <img className={styles.paginationArrow} src="/img/left-btn-gallery.png" alt="" />
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
                                <img className={styles.paginationArrow} src="/img/right-btn-gallery.png" alt="" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    )
}       