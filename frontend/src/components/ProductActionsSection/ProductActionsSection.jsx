import PropTypes from "prop-types";
import { Link } from "react-router-dom";

import sectionStyles from "../shared/sectionLayout.module.css";
import styles from "./ProductActionsSection.module.css";

function ActionControl({ item }) {
  const className = `${styles.action} ${styles[item.emphasis]}`;

  if (item.disabled || !item.href) {
    return (
      <span
        className={`${className} ${styles.disabled}`}
        aria-disabled="true"
        data-design-placeholder={item.id}
      >
        {item.label}
      </span>
    );
  }

  if (item.external) {
    return (
      <a
        className={className}
        href={item.href}
        target="_blank"
        rel="noopener noreferrer"
      >
        {item.label}
        <span aria-hidden="true">↗</span>
      </a>
    );
  }

  return (
    <Link className={className} to={item.href}>
      {item.label}
    </Link>
  );
}

ActionControl.propTypes = {
  item: PropTypes.shape({
    id: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired,
    href: PropTypes.string,
    external: PropTypes.bool,
    disabled: PropTypes.bool,
    emphasis: PropTypes.oneOf(["primary", "secondary", "tertiary"]).isRequired,
  }).isRequired,
};

export default function ProductActionsSection({
  eyebrow,
  title,
  description,
  facts = [],
  items = [],
}) {
  return (
    <section
      className={sectionStyles.section}
      aria-labelledby={`actions-${title}`}
    >
      <div className={sectionStyles.inner}>
        <div className={styles.panel}>
          <div className={styles.copy}>
            {eyebrow && <p className={styles.eyebrow}>{eyebrow}</p>}
            <h2 id={`actions-${title}`} className={styles.title}>
              {title}
            </h2>
            <p className={styles.description}>{description}</p>
          </div>

          {facts.length > 0 && (
            <dl className={styles.facts}>
              {facts.map((fact) => (
                <div className={styles.fact} key={fact.id}>
                  <dt>{fact.label}</dt>
                  <dd>{fact.value}</dd>
                </div>
              ))}
            </dl>
          )}

          <div className={styles.actions}>
            {items.map((item) => (
              <ActionControl item={item} key={item.id} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

ProductActionsSection.propTypes = {
  eyebrow: PropTypes.string,
  title: PropTypes.string.isRequired,
  description: PropTypes.string.isRequired,
  facts: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      value: PropTypes.string.isRequired,
    }),
  ),
  items: PropTypes.arrayOf(ActionControl.propTypes.item),
};
