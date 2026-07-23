import PropTypes from "prop-types";
import { Link } from "react-router-dom";

import styles from "./HeroSection.module.css";

export default function HeroSection({ hero = {} }) {
  return (
    <section className={styles.hero} aria-labelledby="hero-title-v2">
      <div className={styles.overlay} />
      <div className={styles.content}>
        <p className={styles.eyebrow}>{hero.eyebrow || "JouTak Community"}</p>
        <h1 id="hero-title-v2" className={styles.title}>
          {hero.title || "JouTak"}
        </h1>
        <p className={styles.description}>{hero.description}</p>
        <div className={styles.actions}>
          <a
            className={styles["primary-action"]}
            href={hero.primary_cta?.href || "https://joutak.ru"}
            target="_blank"
            rel="noopener noreferrer"
          >
            {hero.primary_cta?.label || "Открыть JouTak"}
          </a>
          <Link
            className={styles["secondary-action"]}
            to={hero.secondary_cta?.to || "/joutak/pay"}
          >
            {hero.secondary_cta?.label || "Оплатить проходку"}
          </Link>
        </div>
        <p className={styles.server}>IP: {hero.server_ip || "mc.joutak.ru"}</p>
      </div>
    </section>
  );
}

HeroSection.propTypes = {
  hero: PropTypes.shape({
    description: PropTypes.string,
    eyebrow: PropTypes.string,
    primary_cta: PropTypes.shape({
      href: PropTypes.string,
      label: PropTypes.string,
    }),
    secondary_cta: PropTypes.shape({
      label: PropTypes.string,
      to: PropTypes.string,
    }),
    server_ip: PropTypes.string,
    title: PropTypes.string,
  }),
};
