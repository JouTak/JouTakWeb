import { Link, Text } from "@gravity-ui/uikit";
import PropTypes from "prop-types";
import { useEffect, useMemo } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

import styles from "./DocumentMarkdown.module.css";
import {
  getDocumentHeadings,
  remarkDocumentHeadings,
} from "./markdownHeadings";

function DocumentLink({ children, href }) {
  return href ? (
    <Link href={href} underline>
      {children}
    </Link>
  ) : (
    <span>{children}</span>
  );
}
DocumentLink.propTypes = { children: PropTypes.node, href: PropTypes.string };

function DocumentParagraph({ children }) {
  return (
    <Text as="p" className={styles.paragraph}>
      {children}
    </Text>
  );
}
DocumentParagraph.propTypes = { children: PropTypes.node };

/* eslint-disable jsx-a11y/no-noninteractive-tabindex -- The scrollable table region needs keyboard access. */
function DocumentTable({ children }) {
  return (
    <div
      className={styles.tableScroll}
      role="region"
      aria-label="Таблица документа"
      tabIndex={0}
    >
      <table>{children}</table>
    </div>
  );
}
/* eslint-enable jsx-a11y/no-noninteractive-tabindex */
DocumentTable.propTypes = { children: PropTypes.node };

function headingComponent(level) {
  function Heading({ children, id }) {
    return (
      <Text as={`h${Math.max(2, level)}`} id={id} className={styles.heading}>
        {children}
      </Text>
    );
  }
  Heading.propTypes = { children: PropTypes.node, id: PropTypes.string };
  return Heading;
}

const components = {
  a: DocumentLink,
  p: DocumentParagraph,
  table: DocumentTable,
  ...Object.fromEntries(
    [1, 2, 3, 4, 5, 6].map((level) => [`h${level}`, headingComponent(level)]),
  ),
};
const plugins = [remarkGfm, remarkDocumentHeadings];

export default function DocumentMarkdown({ markdown }) {
  const headings = useMemo(() => getDocumentHeadings(markdown), [markdown]);
  useEffect(() => {
    let active = true;
    let frame;
    // The route is lazy-loaded: restore deep links after content and fonts mount.
    Promise.resolve(document.fonts?.ready).then(() => {
      if (!active) return;
      let id;
      try {
        id = decodeURIComponent(window.location.hash.slice(1));
      } catch {
        return;
      }
      if (!headings.some((heading) => heading.id === id)) return;
      frame = window.requestAnimationFrame(() => {
        if (active)
          document.getElementById(id)?.scrollIntoView({ block: "start" });
      });
    });
    return () => {
      active = false;
      if (frame !== undefined) window.cancelAnimationFrame(frame);
    };
  }, [headings]);
  return (
    <div className={styles.layout}>
      {headings.length > 0 && (
        <nav className={styles.contents} aria-label="Содержание документа">
          <Text as="h2" variant="subheader-2">
            На этой странице
          </Text>
          <ul>
            {headings.map(({ id, text, depth }) => (
              <li key={id} className={depth === 3 ? styles.nested : undefined}>
                <Link href={`#${id}`}>{text}</Link>
              </li>
            ))}
          </ul>
        </nav>
      )}
      <div className={styles.body}>
        <Markdown remarkPlugins={plugins} components={components} skipHtml>
          {markdown}
        </Markdown>
      </div>
    </div>
  );
}
DocumentMarkdown.propTypes = { markdown: PropTypes.string.isRequired };
