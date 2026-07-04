import LandingPageBuilder from "../components/LandingPageBuilder/LandingPageBuilder";
import FeatureGate from "../features/featureFlags/FeatureGate";
import LegacyJoutak from "../Legacy/frontend/src/pages/ItmoCraft"
import { joutakPageContent } from "./landingContent";

const JouTak = () => {
  return (
  <>
    <FeatureGate
      flag="site_new_homepage"
      fallback={<LegacyJoutak />}
    >
      <LandingPageBuilder sections={joutakPageContent.sections} />
    </FeatureGate>
  </>
  );
};

export default JouTak;
