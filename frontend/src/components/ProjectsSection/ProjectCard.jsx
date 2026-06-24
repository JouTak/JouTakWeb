import PropTypes from "prop-types";
import { Link } from "react-router-dom";

import styles from "./ProjectsSection.module.css";

export default function ProjectCard({
  title,
  description,
  image,
  path,
  extended = false,
}) {
  return (
    <Link
      to={path}
      className={`${styles.card} ${extended ? styles.extended : ""}`}
    >
      {image && (
        <div className={styles.imageWrapper}>
          <img src={image} alt={title} loading="lazy" />
        </div>
      )}
      <div className={styles.projectInfo}>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </Link>
  );
}

ProjectCard.propTypes = {
  description: PropTypes.string.isRequired,
  extended: PropTypes.bool,
  image: PropTypes.string,
  path: PropTypes.string.isRequired,
  title: PropTypes.string.isRequired,
};
