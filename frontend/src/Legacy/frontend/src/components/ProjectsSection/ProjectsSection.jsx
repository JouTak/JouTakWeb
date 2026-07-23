import PropTypes from "prop-types";

import ProjectCard from "./ProjectCard.jsx";
import styles from "./ProjectsSection.module.css";

const PROJECT_IMAGE_BY_PATH = {
  "/itmocraft": "/img/itmocraft.png",
  "/joutak": "/img/joutak.png",
  "/legacy": "/img/legacy.png",
  "/minigames": "/img/minigames.png",
};

export default function ProjectsSection({
  title = "Наши проекты",
  items = [],
}) {
  return (
    <section className={styles.section} aria-labelledby="projects-title-v2">
      <div className={styles.inner}>
        <h2 id="projects-title-v2" className={styles.title}>
          {title}
        </h2>
        <div className={styles.grid}>
          {items.map((project) => (
            <ProjectCard
              key={project.path || project.title}
              {...project}
              image={project.image || PROJECT_IMAGE_BY_PATH[project.path]}
              extended={project.extended || project.path === "/itmocraft"}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

ProjectsSection.propTypes = {
  title: PropTypes.string,
  items: PropTypes.arrayOf(
    PropTypes.shape({
      description: PropTypes.string.isRequired,
      extended: PropTypes.bool,
      image: PropTypes.string,
      path: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired,
    }),
  ),
};
