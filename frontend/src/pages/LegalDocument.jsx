import { Button } from "@gravity-ui/uikit";
import PropTypes from "prop-types";
import { useNavigate } from "react-router-dom";

import {
  PageActions,
  PageNotice,
  PagePanel,
  PageShell,
} from "../components/ui/PageShell.jsx";
import styles from "./LegalDocument.module.css";

const documents = {
  privacy: {
    eyebrow: "Документы",
    title: "Политика конфиденциальности",
    description:
      "Финальная редакция документа готовится к публикации и юридическому согласованию.",
  },
  terms: {
    eyebrow: "Документы",
    title: "Условия использования",
    description:
      "Финальная редакция условий готовится к публикации и юридическому согласованию.",
  },
};

export default function LegalDocument({ documentType }) {
  const navigate = useNavigate();
  const document = documents[documentType] ?? documents.terms;

  return (
    <PageShell
      narrow
      eyebrow={document.eyebrow}
      title={document.title}
      description={document.description}
    >
      <PagePanel className={styles.panel}>
        <PageNotice tone="warning">
          Здесь пока нет утверждённого юридического текста. Мы не подменяем его
          временными формулировками: актуальная версия появится после
          согласования.
        </PageNotice>
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
