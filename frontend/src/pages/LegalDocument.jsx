import { Button, Select, Text } from "@gravity-ui/uikit";
import PropTypes from "prop-types";
import { useNavigate, useSearchParams } from "react-router-dom";

import DocumentMarkdown from "../components/documents/DocumentMarkdown";
import {
  PageActions,
  PageNotice,
  PagePanel,
  PageShell,
} from "../components/ui/PageShell.jsx";
import {
  documents,
  findDocumentVersion,
  formatDocumentDate,
} from "../content/documents/documents";
import styles from "./LegalDocument.module.css";

export default function LegalDocument({ documentType }) {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const document = documents[documentType];
  const version = findDocumentVersion(document, params.get("version"));
  const selectVersion = (id) => {
    setParams((previous) => {
      const next = new URLSearchParams(previous);
      next.set("version", id);
      return next;
    });
  };

  return (
    <PageShell
      className={styles.page}
      contentClassName={styles.content}
      eyebrow="Документы"
      title={document.title}
    >
      <PagePanel
        as="article"
        className={styles.panel}
        aria-label={document.title}
      >
        <div className={styles.toolbar}>
          {version && (
            <dl className={styles.metadata}>
              <div>
                <dt>Автор</dt>
                <dd>{version.author}</dd>
              </div>
              <div>
                <dt>Опубликовано</dt>
                <dd>
                  <time dateTime={version.publishedAt}>
                    {formatDocumentDate(version.publishedAt)}
                  </time>
                </dd>
              </div>
              <div>
                <dt>Обновлено</dt>
                <dd>
                  <time dateTime={version.updatedAt}>
                    {formatDocumentDate(version.updatedAt)}
                  </time>
                </dd>
              </div>
            </dl>
          )}
          <div className={styles.version}>
            <Text as="label" htmlFor={`${documentType}-version`}>
              Редакция документа
            </Text>
            <Select
              id={`${documentType}-version`}
              value={version ? [version.id] : []}
              options={document.versions.map(({ id }) => ({
                value: id,
                content: id,
              }))}
              onUpdate={([id]) => selectVersion(id)}
            />
          </div>
        </div>
        {version ? (
          <>
            {version.id !== document.currentVersion && (
              <PageNotice>
                Архивная редакция.{" "}
                <Button
                  view="flat"
                  onClick={() => selectVersion(document.currentVersion)}
                >
                  Открыть текущую
                </Button>
              </PageNotice>
            )}
            <DocumentMarkdown key={version.id} markdown={version.markdown} />
          </>
        ) : (
          <PageNotice tone="warning">
            <Text as="p">Такая редакция документа не найдена.</Text>
            <Button
              view="normal"
              onClick={() => selectVersion(document.currentVersion)}
            >
              Открыть текущую редакцию
            </Button>
          </PageNotice>
        )}
        <PageActions>
          <Button view="action" size="l" onClick={() => navigate("/")}>
            На главную ITMOcraft
          </Button>
          <Button view="outlined" size="l" onClick={() => navigate("/contact")}>
            Связаться с нами
          </Button>
        </PageActions>
      </PagePanel>
    </PageShell>
  );
}
LegalDocument.propTypes = {
  documentType: PropTypes.oneOf(["privacy", "terms"]).isRequired,
};
