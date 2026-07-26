import ResponsiveMedia from "../../media/ResponsiveMedia";
import Notification from "../Notification/Notification";
import styles from "./MainSection.module.scss";

export default function MainSection({
  backgroundImage = "/img/main-image.png",
  backgroundMedia,
  logoSrc = "/img/logo-maxi.svg",
  logoMedia,
  logoAlt = "ITMO CRAFT",
  notificationUpperText = "Комьюнити",
  notificationLowerText = "Больше, чем просто сервер!",
  showNotification = true,
}) {
  return (
    <div className={styles.mainSection}>
      {backgroundMedia ? (
        <ResponsiveMedia
          media={backgroundMedia}
          alt=""
          eager
          sizes="100vw"
          pictureClassName={styles.backgroundMedia}
          className={styles.backgroundImage}
        />
      ) : (
        <div
          className={styles.backgroundMedia}
          style={{ backgroundImage: `url('${backgroundImage}')` }}
        />
      )}
      {showNotification && (
        <Notification
          upperText={notificationUpperText}
          lowerText={notificationLowerText}
        />
      )}
      <div className={styles.mainSectionInner}>
        {logoMedia ? (
          <ResponsiveMedia media={logoMedia} alt={logoAlt} eager />
        ) : (
          <img src={logoSrc} alt={logoAlt} />
        )}
      </div>
    </div>
  );
}
