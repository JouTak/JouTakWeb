import Notification from "../Notification/Notification";
import styles from "./MainSection.module.scss";

export default function MainSection({
  backgroundImage = "/img/main-image.png",
  logoSrc = "/img/logo-maxi.svg",
  logoAlt = "ITMO CRAFT",
  notificationUpperText = "Комьюнити",
  notificationLowerText = "Больше, чем просто сервер!",
  showNotification = true,
}) {
  return (
    <div
      className={styles.mainSection}
      style={{ backgroundImage: `url('${backgroundImage}')` }}
    >
      {showNotification && (
        <Notification
          upperText={notificationUpperText}
          lowerText={notificationLowerText}
        />
      )}
      <div className={styles.mainSectionInner}>
        <img src={logoSrc} alt={logoAlt} />
      </div>
    </div>
  );
}
