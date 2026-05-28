import styles from './MainSection.module.css';
import Notification from '../Notification/Notification';

export default function MainSection({
  backgroundImage = '/img/main-image.png',
  logoSrc = '/img/logo-maxi.svg',
  logoAlt = 'ITMO CRAFT',
  notificationUpperText = 'Комьюнити',
  notificationLowerText = 'Больше, чем просто сервер!',
  showNotification = true,
}) {
  return (
    <div
      className={styles.mainSection}
      style={{ backgroundImage: `url('${backgroundImage}')` }}
    >
      <div className={styles.mainSectionInner}>
        <img src={logoSrc} alt={logoAlt} />
        {showNotification && (
          <Notification
            upperText={notificationUpperText}
            lowerText={notificationLowerText}
          />
        )}
      </div>
    </div>
  );
}