import { Loader } from "@gravity-ui/uikit";
import clsx from "clsx";
import PropTypes from "prop-types";

import styles from "./PageShell.module.css";

export function PageShell({
  children,
  className,
  contentClassName,
  description,
  eyebrow = "ITMOcraft",
  narrow = false,
  title,
}) {
  return (
    <section className={clsx(styles.page, className)}>
      <div className={styles.pixelGlow} aria-hidden="true" />
      <div
        className={clsx(
          styles.container,
          narrow && styles.containerNarrow,
          contentClassName,
        )}
      >
        {(title || description) && (
          <header className={styles.header}>
            {eyebrow && <span className={styles.eyebrow}>{eyebrow}</span>}
            {title && <h1 className={styles.title}>{title}</h1>}
            {description && <p className={styles.description}>{description}</p>}
          </header>
        )}
        {children}
      </div>
    </section>
  );
}

PageShell.propTypes = {
  children: PropTypes.node.isRequired,
  className: PropTypes.string,
  contentClassName: PropTypes.string,
  description: PropTypes.node,
  eyebrow: PropTypes.string,
  narrow: PropTypes.bool,
  title: PropTypes.string,
};

export function PagePanel({
  as: Component = "section",
  children,
  className,
  ...props
}) {
  return (
    <Component className={clsx(styles.panel, className)} {...props}>
      {children}
    </Component>
  );
}

PagePanel.propTypes = {
  as: PropTypes.elementType,
  children: PropTypes.node.isRequired,
  className: PropTypes.string,
};

export function PageActions({ children, className }) {
  return <div className={clsx(styles.actions, className)}>{children}</div>;
}

PageActions.propTypes = {
  children: PropTypes.node.isRequired,
  className: PropTypes.string,
};

export function PageNotice({ children, className, tone = "info" }) {
  return (
    <div
      className={clsx(styles.notice, styles[`notice-${tone}`], className)}
      role={tone === "danger" ? "alert" : "status"}
    >
      {children}
    </div>
  );
}

PageNotice.propTypes = {
  children: PropTypes.node.isRequired,
  className: PropTypes.string,
  tone: PropTypes.oneOf(["danger", "info", "success", "warning"]),
};

export function StatePage({
  actions,
  description,
  eyebrow,
  icon = "?",
  title,
}) {
  return (
    <PageShell narrow eyebrow={eyebrow} title={title} description={description}>
      <PagePanel className={styles.statePanel}>
        <span className={styles.stateIcon} aria-hidden="true">
          {icon}
        </span>
        {actions && <PageActions>{actions}</PageActions>}
      </PagePanel>
    </PageShell>
  );
}

StatePage.propTypes = {
  actions: PropTypes.node,
  description: PropTypes.node.isRequired,
  eyebrow: PropTypes.string,
  icon: PropTypes.node,
  title: PropTypes.string.isRequired,
};

export function LoadingPage({ description = "Подготавливаем страницу" }) {
  return (
    <PageShell
      narrow
      title="Загружаем…"
      description={description}
      eyebrow="Пожалуйста, подождите"
    >
      <PagePanel className={styles.loadingPanel} aria-live="polite">
        <Loader size="l" />
        <span>Собираем актуальные данные и настройки интерфейса</span>
      </PagePanel>
    </PageShell>
  );
}

LoadingPage.propTypes = {
  description: PropTypes.string,
};
