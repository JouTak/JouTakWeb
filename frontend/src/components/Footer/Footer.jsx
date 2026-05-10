import { FaDiscord, FaTelegramPlane, FaVk } from "react-icons/fa";
import styles from "./Footer.module.css";

const CustomFooter = () => {
  return (
    <>
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <div className={styles.logoWrap}>
          <img src="/img/logo-maxi.svg" alt="ITMOcraft" className={styles.logo} />
        </div>

        <div className={styles.navCol}>
          <h3 className={styles.heading}>Навигация</h3>
          <a href="#" className={styles.subitem}>JouTak</a>
          <a href="#" className={styles.subitem}>MiniGames</a>
          <a href="#" className={styles.subitem}>Legacy</a>
          <a href="#" className={`${styles.subitem} ${styles.subitemLast}`}>ITMOcraft</a>
        </div>

        <div className={styles.contactsCol}>
          <h3 className={styles.heading}>Связь с нами</h3>
          <a href="#" className={styles.subitem}>Контакты</a>
          <a href="#" className={styles.subitem}>Наша команда</a>
          <a href="#" className={`${styles.subitem} ${styles.subitemLast}`}>Документы</a>
        </div>

        <div className={styles.socialCol}>
          <div className={styles.socialRow}>
            <div className={styles.socialIcon}>
              <FaVk />
            </div>
            <div className={styles.socialIcon}>
              <FaTelegramPlane />
            </div>
            <div className={styles.socialIcon}>
              <FaDiscord />
            </div>
          </div>

          <a href="#" className={styles.copyright}>
            Copyright © {new Date().getFullYear()} iTMOcraft
          </a>
        </div>
      </div>
    </footer>
    <img src="img/footer.svg" alt="" />
    </>
  );
};

export default CustomFooter;
