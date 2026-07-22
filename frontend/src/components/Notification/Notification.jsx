import styles from "./Notification.module.scss";

export default function Notification({ upperText, lowerText }) {
  return (
    <div className={styles.notificationContainer}>
      <div className={styles.notificationInner}>
        <div className={styles.up}>
          <p>{upperText}</p>
        </div>

        <div className={styles.down}>
          <p>{lowerText}</p>
        </div>
      </div>
    </div>
  );
}
