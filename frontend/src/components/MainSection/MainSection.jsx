import styles from './MainSection.module.css';

export default function MainSection() {
  return (
    <div className={styles.mainSection}>
      <div className={styles.mainSectionInner}>
        <h1 className={styles.mainSectionTitle}>Main Section</h1>
      </div>
    </div>
  );
}