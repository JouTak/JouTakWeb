import { useState } from "react";
import styles from "./ThemeSwitcher.module.css";

export default function ThemeSwitcher() {
  const [isNight, setIsNight] = useState(false);

  return (
    <button
      type="button"
      className={`${styles.themeSwitcherGrid} ${isNight ? styles.nightTheme : ""}`}
      id="theme-switcher-grid"
      aria-label="Switch theme"
      onClick={() => setIsNight((prev) => !prev)}
    >
      <div className={styles.sun} id="sun" aria-hidden="true"></div>
      <div
        className={styles.moonOverlay}
        id="moon-overlay"
        aria-hidden="true"
      ></div>
      <div
        className={`${styles.cloudBall} ${styles.cloudBallLeft}`}
        id="ball1"
        aria-hidden="true"
      ></div>
      <div
        className={`${styles.cloudBall} ${styles.cloudBallMiddle}`}
        id="ball2"
        aria-hidden="true"
      ></div>
      <div
        className={`${styles.cloudBall} ${styles.cloudBallRight}`}
        id="ball3"
        aria-hidden="true"
      ></div>
      <div
        className={`${styles.cloudBall} ${styles.cloudBallTop}`}
        id="ball4"
        aria-hidden="true"
      ></div>
      <div className={styles.star1} id="star1" aria-hidden="true"></div>
      <div className={styles.star2} id="star2" aria-hidden="true"></div>
      <div className={styles.star3} id="star3" aria-hidden="true"></div>
      <div className={styles.star4} id="star4" aria-hidden="true"></div>
    </button>
  );
}
