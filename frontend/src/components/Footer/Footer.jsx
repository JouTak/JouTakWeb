import { FaDiscord, FaTelegramPlane, FaVk } from "react-icons/fa";
import styles from "./Footer.module.css";

const SOCIAL_ICON_BY_TYPE = {
  vk: FaVk,
  telegram: FaTelegramPlane,
  discord: FaDiscord,
};

const defaultNavigationItems = [
  { label: "JouTak", href: "/joutak" },
  { label: "MiniGames", href: "/minigames" },
  { label: "Legacy", href: "/legacy" },
  { label: "ITMOcraft", href: "/itmocraft" },
];

const defaultContactItems = [
  { label: "Контакты", href: "/contact" },
  { label: "Наша команда", href: "/team" },
  { label: "Документы", href: "/documents" },
];

const defaultSocialItems = [
  { type: "vk", href: "https://vk.com/itmocraft" },
  { type: "telegram", href: "https://t.me/itmocraft" },
  { type: "discord", href: "https://discord.com/invite/2tPbdRVgcz" },
];

const CustomFooter = ({
  logoSrc = "/img/logo-maxi.svg",
  logoAlt = "ITMOcraft",
  navigationTitle = "Навигация",
  navigationItems = defaultNavigationItems,
  contactsTitle = "Связь с нами",
  contactItems = defaultContactItems,
  socialItems = defaultSocialItems,
  copyrightText = `Copyright © ${new Date().getFullYear()} iTMOcraft`,
  bottomImageSrc = "img/footer.svg",
}) => {
  return (
    <>
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <div className={styles.logoWrap}>
          <img src={logoSrc} alt={logoAlt} className={styles.logo} />
        </div>

        <div className={styles.navCol}>
          <h3 className={styles.heading}>{navigationTitle}</h3>
          {navigationItems.map((item, index) => (
            <a
              key={`${item.label}-${index}`}
              href={item.href}
              className={`${styles.subitem} ${index === navigationItems.length - 1 ? styles.subitemLast : ""}`}
            >
              {item.label}
            </a>
          ))}
        </div>

        <div className={styles.contactsCol}>
          <h3 className={styles.heading}>{contactsTitle}</h3>
          {contactItems.map((item, index) => (
            <a
              key={`${item.label}-${index}`}
              href={item.href}
              className={`${styles.subitem} ${index === contactItems.length - 1 ? styles.subitemLast : ""}`}
            >
              {item.label}
            </a>
          ))}
        </div>

        <div className={styles.socialCol}>
          <div className={styles.socialRow}>
            {socialItems.map(({ type, href }, index) => {
              const Icon = SOCIAL_ICON_BY_TYPE[type];

              if (!Icon) {
                return null;
              }

              return (
                <div key={`${type}-${index}`} className={styles.socialIcon}>
                  <a href={href} target="_blank" rel="noopener noreferrer">
                    <Icon />
                  </a>
                </div>
              );
            })}
          </div>

          <a href="#" className={styles.copyright}>
            {copyrightText}
          </a>
        </div>
      </div>
    </footer>
    <img src={bottomImageSrc} alt="" />
    </>
  );
};

export default CustomFooter;
