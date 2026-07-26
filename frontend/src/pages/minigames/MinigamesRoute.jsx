import { usePageDocument } from "../../features/pageDocument/pageDocumentContext";
import MinigamesV2Page from "./MinigamesV2Page";
import SimpleMinigamesPage from "./SimpleMinigamesPage";

export default function MinigamesRoute() {
  const { document, loading } = usePageDocument();
  if (loading && !document) {
    return <div className="py-5 text-center text-secondary">Загрузка...</div>;
  }
  return document?.effective_page_variant === "v2" ? (
    <MinigamesV2Page />
  ) : (
    <SimpleMinigamesPage />
  );
}
