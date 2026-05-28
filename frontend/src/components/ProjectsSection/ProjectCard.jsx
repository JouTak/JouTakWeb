import { Link } from 'react-router-dom'
import styles from './projectCard.module.css'
import clsx from 'clsx'

export default function ProjectCard({
    title,
    description,
    image,
    to,
    extended = false,
    imageHeight
}) {
    const imageStyle = imageHeight
        ? { height: imageHeight, aspectRatio: "auto" }
        : undefined

    return (
    <Link to={to} 
          className={clsx(styles.card, {[styles.extended]: extended})}>

        <div className={styles.imageWrapper}>
            <img src={image} alt={title} style={imageStyle} />
        </div>

        <div className={styles.projectInfo}>
            <h3>{title}</h3>
            <p>{description}</p>
        </div>

    </Link>

    )
}