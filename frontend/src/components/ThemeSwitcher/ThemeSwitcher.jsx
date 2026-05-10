import { useState } from "react";
import styles from "./ThemeSwitcher.module.css";

export default function ThemeSwitcher() {
  const [isNight, setIsNight] = useState(true);

  return (
    <button
      type="button"
      className={`${styles.switch} ${isNight ? styles.night : ""}`}
      onClick={() => setIsNight((prev) => !prev)}
      aria-label="Switch theme"
    >
      {/* Контур */}
      <svg
        className={styles.contour}
        viewBox="0 0 95 48"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect x="8" y="36" width="4" height="4" fill="white" />
        <rect
          width="4"
          height="4"
          transform="matrix(-1 0 0 1 87 36)"
          fill="white"
        />
        <rect
          x="12"
          y="8"
          width="4"
          height="4"
          transform="rotate(90 12 8)"
          fill="white"
        />
        <rect
          width="4"
          height="4"
          transform="matrix(0 1 1 0 83 8)"
          fill="white"
        />
        <rect x="12" y="40" width="8" height="4" fill="white" />
        <rect
          width="8"
          height="4"
          transform="matrix(-1 0 0 1 83 40)"
          fill="white"
        />
        <rect
          x="8"
          y="12"
          width="8"
          height="4"
          transform="rotate(90 8 12)"
          fill="white"
        />
        <rect
          width="8"
          height="4"
          transform="matrix(0 1 1 0 87 12)"
          fill="white"
        />
        <rect x="20" y="44" width="55" height="4" fill="white" />
        <rect x="20" width="55" height="4" fill="white" />
        <rect x="4" y="28" width="4" height="8" fill="white" />
        <rect
          width="4"
          height="8"
          transform="matrix(-1 0 0 1 91 28)"
          fill="white"
        />
        <rect
          x="20"
          y="4"
          width="4"
          height="8"
          transform="rotate(90 20 4)"
          fill="white"
        />
        <rect
          width="4"
          height="8"
          transform="matrix(0 1 1 0 75 4)"
          fill="white"
        />
        <rect y="20" width="4" height="8" fill="white" />
        <rect
          width="4"
          height="8"
          transform="matrix(-1 0 0 1 95 20)"
          fill="white"
        />
      </svg>

      {/* Звезды */}
      <svg
        className={styles.stars}
        viewBox="0 0 40 35"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect x="18" y="16" width="2" height="2" fill="white" />
        <rect x="27" y="28" width="2" height="2" fill="white" />
        <rect x="33" y="33" width="2" height="2" fill="white" />
        <rect y="9" width="2" height="2" fill="white" />
        <rect x="37" y="3" width="3" height="3" fill="white" />
        <rect x="18" width="3" height="3" fill="white" />
        <rect x="6" y="23" width="3" height="3" fill="white" />
        <rect x="10" y="8" width="2" height="2" fill="white" />
        <rect x="29" y="7" width="3" height="3" fill="white" />
      </svg>

      {/* Ползунок */}
      <div className={styles.thumb}>
        {/* Фон ползунка */}
        <svg
          className={styles.thumbBg}
          viewBox="0 0 87 40"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M0 24V16H4V8H8V4H16V0H71V4H79V8H83V16H87V24H83V32H79V36H71V40H16V36H8V32H4V24H0Z"
            fill="currentColor"
          />
        </svg>

        {/* Солнце */}
        <svg
          className={styles.sun}
          viewBox="0 0 30 30"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M7.42578 20.198V9.80199H9.80202V7.42575H20.1981V9.80199H22.5743V20.198H20.1981V22.5743H9.80202V20.198H7.42578Z"
            fill="currentColor"
          />
          <rect y="13.3663" width="5.0495" height="2.9703" fill="currentColor" />
          <rect
            x="16.3365"
            width="5.0495"
            height="2.9703"
            transform="rotate(90 16.3365 0)"
            fill="currentColor"
          />
          <rect
            x="16.3365"
            y="24.9505"
            width="5.0495"
            height="2.9703"
            transform="rotate(90 16.3365 24.9505)"
            fill="currentColor"
          />
          <rect
            x="24.9504"
            y="13.3663"
            width="5.0495"
            height="2.9703"
            fill="currentColor"
          />
          <rect
            x="5.04956"
            y="22.5742"
            width="2.37624"
            height="2.37624"
            fill="currentColor"
          />
          <rect
            x="24.9504"
            y="2.67328"
            width="2.37624"
            height="2.37624"
            fill="currentColor"
          />
          <rect
            x="7.42578"
            y="5.0495"
            width="2.37624"
            height="2.37624"
            transform="rotate(90 7.42578 5.0495)"
            fill="currentColor"
          />
          <rect
            x="27.3268"
            y="24.9505"
            width="2.37624"
            height="2.37624"
            transform="rotate(90 27.3268 24.9505)"
            fill="currentColor"
          />
          <rect
            x="2.67322"
            y="24.9505"
            width="2.37624"
            height="2.37624"
            fill="currentColor"
          />
          <rect
            x="22.5742"
            y="5.0495"
            width="2.37624"
            height="2.37624"
            fill="currentColor"
          />
          <rect
            x="5.04956"
            y="2.67328"
            width="2.37624"
            height="2.37624"
            transform="rotate(90 5.04956 2.67328)"
            fill="currentColor"
          />
          <rect
            x="24.9504"
            y="22.5742"
            width="2.37624"
            height="2.37624"
            transform="rotate(90 24.9504 22.5742)"
            fill="currentColor"
          />
        </svg>

        {/* Луна */}
        <svg
          className={styles.moon}
          viewBox="0 0 30 30"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M2.14953 13.875H0V20.0625H2.14953V24H4.01869V26.0625H6.07477V28.125H10V30H20.0935V28.125H24.0187V26.0625H26.0748V24H27.9439L28.1308 20.0625H30V9.9375H27.9439V6H26.0748V3.9375H24.0187V2.0625H19.9065V0H14.1121V2.0625H15.9813V3.9375H18.0374V6H19.9065V15.9375H18.0374V18H15.9813V20.0625H6.07477V18H4.01869V15.9375H2.14953V13.875Z"
            fill="currentColor"
          />
        </svg>

        <svg
          className={styles.clouds}
          width="23" 
          height="14" 
          viewBox="0 0 23 14"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path d="M0 10V6H2V4H4V2H6V0H17V2H19V4H21V6H23V10H21V12H19V14H4V12H2V10H0Z" fill="currentColor" />
        </svg>
      </div>
    </button>
  );
}