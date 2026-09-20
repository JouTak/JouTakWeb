import { Button } from "@gravity-ui/uikit";
import PropTypes from "prop-types";
import { useNavigate } from "react-router-dom";

import {
  PageActions,
  PagePanel,
  PageShell,
} from "../components/ui/PageShell.jsx";
import styles from "./LegalDocument.module.css";

const documents = {
  privacy: {
    title: "Политика конфиденциальности",
    sections: [
      "Общие положения",
      "Какие данные мы получаем",
      "Как используются данные",
      "Хранение и защита данных",
      "Обратная связь",
    ],
  },
  terms: {
    title: "Условия использования",
    sections: [
      "Общие положения",
      "Учётная запись",
      "Правила использования",
      "Изменения условий",
      "Обратная связь",
    ],
  },
};

// Preview content and metadata; replace together with the published document.
const previewParagraphs = [
  "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer vitae justo eget magna fermentum iaculis. Sed euismod, nibh vitae cursus tincidunt, velit lorem consequat neque, at facilisis ipsum neque vel mauris. Praesent feugiat tellus sit amet sapien tincidunt, vel dignissim erat volutpat.",
  "Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Donec ullamcorper, justo at viverra tincidunt, augue sem malesuada est, sed sollicitudin lectus sapien non urna. Curabitur vitae lacus a erat posuere tincidunt.",
];

export default function LegalDocument({ documentType }) {
  const navigate = useNavigate();
  const document = documents[documentType] ?? documents.terms;

  return (
    <PageShell
      className={styles.page}
      contentClassName={styles.content}
      eyebrow="Документы · макет"
      title={document.title}
    >
      <dl className={styles.metadata}>
        <div>
          <dt>Автор</dt>
          <dd>Команда JouTak</dd>
        </div>
        <div>
          <dt>Опубликовано</dt>
          <dd>
            <time dateTime="2026-09-21">21 сентября 2026</time>
          </dd>
        </div>
        <div>
          <dt>Обновлено</dt>
          <dd>
            <time dateTime="2026-09-21">21 сентября 2026</time>
          </dd>
        </div>
      </dl>
      <PagePanel
        as="article"
        className={styles.panel}
        aria-label={document.title}
      >
        <p className={styles.caption}>Демонстрационный текст</p>
        <nav className={styles.contents} aria-label="Содержание документа">
          <h2>Содержание</h2>
          <ol>
            {document.sections.map((heading, index) => (
              <li key={heading}>
                <a href={`#document-section-${index + 1}`}>{heading}</a>
              </li>
            ))}
          </ol>
        </nav>
        {document.sections.map((heading, index) => (
          <section className={styles.section} key={heading}>
            <h2 id={`document-section-${index + 1}`}>
              {index + 1}. {heading}
            </h2>
            {previewParagraphs.map((paragraph) => (
              <p lang="la" key={paragraph}>
                {paragraph}
              </p>
            ))}
          </section>
        ))}
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
