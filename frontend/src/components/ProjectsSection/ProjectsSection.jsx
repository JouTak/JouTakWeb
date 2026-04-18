import ProjectCard from './ProjectCard'
import styles from './projectCard.module.css'
import sectionStyles from '../shared/sectionLayout.module.css'
import projects from './projects.data.js'

export default function ProjectsSection() {
    return (
        <section className={sectionStyles.section}>
            <div className={sectionStyles.inner}>
                <h2 className={`${sectionStyles.title} ${styles.title}`}>Наши проекты</h2>

                <div className={styles.grid}>
                    {projects.map(project => (
                        <ProjectCard key={project.title} {...project}/>
                    ))}
                </div>
            </div>
        </section>
    )
}