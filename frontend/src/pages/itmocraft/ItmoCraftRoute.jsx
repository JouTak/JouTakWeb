import PropTypes from "prop-types";

import { usePageDocument } from "../../features/pageDocument/pageDocumentContext";
import ItmoCraftV2Page from "./ItmoCraftV2Page";
import SimpleItmoCraftPage from "./SimpleItmoCraftPage";

export default function ItmoCraftRoute({ legacyAlias = false }) {
  const { document, loading } = usePageDocument();
  if (legacyAlias) return <SimpleItmoCraftPage />;
  if (loading && !document) {
    return <div className="py-5 text-center text-secondary">Загрузка...</div>;
  }
  return document?.effective_page_variant === "v2" ? (
    <ItmoCraftV2Page />
  ) : (
    <SimpleItmoCraftPage />
  );
}

ItmoCraftRoute.propTypes = {
  legacyAlias: PropTypes.bool,
};
