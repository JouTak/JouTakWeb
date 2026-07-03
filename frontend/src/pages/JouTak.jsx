import LandingPageBuilder from "../components/LandingPageBuilder/LandingPageBuilder";
import FeatureGate from "../features/featureFlags/FeatureGate";
import LegacyItmoCraft from "../Legacy/frontend/src/pages/ItmoCraft.jsx"
import { joutakPageContent } from "./landingContent";

const JouTak = () => {
  return (
  <>
    <FeatureGate
      flag="site_new_itmocraft_page"
      fallback={<LegacyItmoCraft />}
    >
      <LandingPageBuilder sections={joutakPageContent.sections} />
    </FeatureGate>
  </>
  );
};

export default JouTak;
