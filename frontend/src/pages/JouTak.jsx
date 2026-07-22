import LandingPageBuilder from "../components/LandingPageBuilder/LandingPageBuilder";
import FeatureGate from "../features/featureFlags/FeatureGate";
import LegacyJoutak from "../Legacy/frontend/src/pages/JouTak";
import { joutakPageContent } from "./landingContent";

const JouTak = () => {
  return (
    <FeatureGate
      flag="site_joutak_page_version"
      flag_type="variant"
      variants={{
        legacy: <LegacyJoutak />,
        v2: <LandingPageBuilder sections={joutakPageContent.sections} />,
      }}
      fallback={<LegacyJoutak />}
    />
  );
};

export default JouTak;
