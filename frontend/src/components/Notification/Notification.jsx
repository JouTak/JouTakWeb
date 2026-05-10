import styles from "./Notification.module.css";

export default function Notification({upperText, lowerText}) {
    return(
        <div className={styles.notification}>
            <div className={styles.up}>
                <p>{upperText}</p>
            </div>

            <div className={styles.down}>
                <p>{lowerText}</p>
            </div>
        </div>
    )
}