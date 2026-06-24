import PropTypes from "prop-types";
import { Link } from "react-router-dom";

import styles from "./FooterV2.module.css";

const navigation = [
  ["JouTak", "/joutak"],
  ["MiniGames", "/minigames"],
  ["Legacy", "/legacy"],
  ["ITMOcraft", "/itmocraft"],
];

const contacts = [
  ["Контакты", "/contact"],
  ["Политика конфиденциальности", "/privacy-policy"],
  ["Условия использования", "/terms-of-use"],
];

const socials = [
  ["VK", "https://vk.com/itmocraft", "/img/icons/vk.svg"],
  ["Telegram", "https://t.me/itmocraft", "/img/icons/tg.svg"],
  [
    "Discord",
    "https://discord.com/invite/2tPbdRVgcz",
    "/img/icons/discord.svg",
  ],
];

function LinkColumn({ title, items }) {
  return (
    <nav aria-label={title}>
      <h2 className={styles.heading}>{title}</h2>
      <ul className={styles.links}>
        {items.map(([label, href]) => (
          <li key={href}>
            <Link to={href}>{label}</Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

LinkColumn.propTypes = {
  title: PropTypes.string.isRequired,
  items: PropTypes.arrayOf(PropTypes.arrayOf(PropTypes.string)).isRequired,
};

export default function FooterV2() {
  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <Link className={styles.brand} to="/joutak" aria-label="JouTak">
          <img src="/img/logo-maxi.svg" alt="" />
        </Link>
        <LinkColumn title="Навигация" items={navigation} />
        <LinkColumn title="Связь с нами" items={contacts} />
        <div className={styles["social-column"]}>
          <div className={styles.socials}>
            {socials.map(([label, href, icon]) => (
              <a
                key={href}
                href={href}
                aria-label={label}
                target="_blank"
                rel="noopener noreferrer"
              >
                <img src={icon} alt="" />
              </a>
            ))}
          </div>
          <p>© {new Date().getFullYear()} ITMOcraft</p>
        </div>
      </div>
    </footer>
  );
}
