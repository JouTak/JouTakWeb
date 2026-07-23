import LandingPageBuilder from "../components/LandingPageBuilder/LandingPageBuilder";
import FeatureGate from "../features/featureFlags/FeatureGate";
import LegacyMinigames from "../Legacy/frontend/src/pages/Minigames.jsx";
import { miniGamesPageContent } from "./landingContent";

const MiniGames = () => {
  return (
    <>
      <FeatureGate
        flag="site_minigames_page_version"
        flag_type="variant"
        variants={{
          v2: <LandingPageBuilder sections={miniGamesPageContent.sections} />,
          legacy: <LegacyMinigames />,
        }}
        fallback={<LegacyMinigames />}
      />
    </>
  );
};

export default MiniGames;
