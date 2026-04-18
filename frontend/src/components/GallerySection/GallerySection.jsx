import { useState } from 'react'
import sectionStyles from '../shared/sectionLayout.module.css'
import styles from './gallery.module.css'

export default function GallerySection() {
    const galleryItems = [
        { label: 'JouTak SMP', image: '/img/gallery-bg.png', buttonClass: styles.buttonOne },
        { label: 'ITMOcraft', image: '/img/gallery-bg-2.png', buttonClass: styles.buttonTwo },
        { label: 'MiniGames', image: '/img/gallery-bg-3.png', buttonClass: styles.buttonThree },
        { label: 'Legacy', image: '/img/gallery-bg-4.png', buttonClass: styles.buttonFour },
    ]

    const [activeIndex, setActiveIndex] = useState(0)

    return (
        <section className={sectionStyles.section}>
            <div className={sectionStyles.inner}>
                <h2 className={sectionStyles.title}>Галерея проектов</h2>
                <div className={styles.gallery}>
                    <img className={styles.galleryImage} src={galleryItems[activeIndex].image} alt="Gallery main view" />
                    {galleryItems.map((item, index) => (
                        <button
                            key={item.label}
                            className={`${styles.galleryButton} ${item.buttonClass} ${
                                activeIndex === index ? styles.chosenButton : ''
                            }`}
                            onClick={() => setActiveIndex(index)}
                            type="button"
                        >
                            {item.label}
                        </button>
                    ))}
                </div>
            </div>
        </section>
    )
}       