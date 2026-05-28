import ProjectCard from './ProjectCard'
import styles from './projectCard.module.css'
import sectionStyles from '../shared/sectionLayout.module.css'

export default function ProjectsSection({
    title = 'Наши проекты',
    projects = [],
}) {
    return (
        <section className={sectionStyles.section}>
            <div className={sectionStyles.inner}>
                <h2 className={`${sectionStyles.title} ${styles.title}`}>{title}</h2>

                <div className={styles.grid}>
                    {projects.map(project => (
                        <ProjectCard key={project.title} {...project}/>
                    ))}
                </div>
            </div>
        </section>
    )
}