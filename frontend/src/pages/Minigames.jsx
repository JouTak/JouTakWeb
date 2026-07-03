import LandingPageBuilder from "../components/LandingPageBuilder/LandingPageBuilder";
import FeatureGate from "../features/featureFlags/FeatureGate";
import LegacyMinigames from "../Legacy/frontend/src/pages/Minigames.jsx"
import { miniGamesPageContent } from "./landingContent";

const MiniGames = () => {
  return (
  <>
    <FeatureGate
      flag="site_new_minigames_page"
      fallback={<LegacyMinigames />}
    >
      <LandingPageBuilder sections={miniGamesPageContent.sections} />
    </FeatureGate>
  </>
  );
};

export default MiniGames;
