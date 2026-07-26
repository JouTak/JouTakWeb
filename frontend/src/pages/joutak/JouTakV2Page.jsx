import LandingPageBuilder from "../../components/LandingPageBuilder/LandingPageBuilder";
import { usePageDocument } from "../../features/pageDocument/pageDocumentContext";

export default function JouTakV2Page() {
  const { document } = usePageDocument();
  return <LandingPageBuilder sections={document?.content?.sections ?? []} />;
}
