import PageLoading from "../../components/PageLoading";
import { usePageDocument } from "../../features/pageDocument/pageDocumentContext";
import JouTakV2Page from "./JouTakV2Page";
import SimpleJoutakPage from "./SimpleJoutakPage";

export default function JouTakRoute() {
  const { document, loading } = usePageDocument();
  if (loading && !document) {
    return <PageLoading />;
  }
  return document?.effective_page_variant === "v2" ? (
    <JouTakV2Page />
  ) : (
    <SimpleJoutakPage />
  );
}
