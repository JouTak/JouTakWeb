import ProjectCard from './ProjectCard'
import styles from './projectCard.module.css'
import projects from './projects.data.js'

export default function ProjectsSection() {
    return (
        <section className={styles.section}>
            <h2 className={styles.title}>Наши проекты</h2>

            <div className={styles.grid}>
                {projects.map(project => (
                    <ProjectCard key={project.title} {...project}/>
                ))}
            </div>
        </section>
    )
}