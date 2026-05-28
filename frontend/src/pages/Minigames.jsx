import LandingPageBuilder from "../components/LandingPageBuilder/LandingPageBuilder";
import { miniGamesPageContent } from "./landingContent";

const MiniGames = () => {
  return <LandingPageBuilder sections={miniGamesPageContent.sections} />;
};

export default MiniGames;
