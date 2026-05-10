import styles from './MainSection.module.css';
import Notification from '../Notification/Notification';

export default function MainSection() {
  return (
    <div className={styles.mainSection}>
      <div className={styles.mainSectionInner}>
        <img src="/img/logo-maxi.svg" alt="ITMO CRAFT" />
        <Notification upperText="Комьюнити" lowerText="Больше, чем просто сервер!"/>
      </div>
    </div>
  );
}