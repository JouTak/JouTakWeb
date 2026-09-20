import PropTypes from "prop-types";

import PageLoading from "../../components/PageLoading";
import { usePageDocument } from "../../features/pageDocument/pageDocumentContext";
import ItmoCraftV2Page from "./ItmoCraftV2Page";
import SimpleItmoCraftPage from "./SimpleItmoCraftPage";

export default function ItmoCraftRoute({ legacyAlias = false }) {
  const { document, loading } = usePageDocument();
  if (legacyAlias) return <SimpleItmoCraftPage />;
  if (loading && !document) {
    return <PageLoading />;
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
