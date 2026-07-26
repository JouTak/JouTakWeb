import { usePageDocument } from "../../features/pageDocument/pageDocumentContext";
import JouTakV2Page from "./JouTakV2Page";
import SimpleJoutakPage from "./SimpleJoutakPage";

export default function JouTakRoute() {
  const { document, loading } = usePageDocument();
  if (loading && !document) {
    return <div className="py-5 text-center text-secondary">Загрузка...</div>;
  }
  return document?.effective_page_variant === "v2" ? (
    <JouTakV2Page />
  ) : (
    <SimpleJoutakPage />
  );
}
