import { lazy } from "react";

import MinecraftButton from "../components/MinecraftButton/MinecraftButton";
import sectionStyles from "../components/shared/sectionLayout.module.css";
import FeatureGate from "../features/featureFlags/FeatureGate";
import { itmocraftPageContent } from "./landingContent";
const ITMOcraftLegacy = lazy(
  () => import("../Legacy/frontend/src/pages/ItmoCraft"),
);
const styles = lazy(() => import("./ItmoCraft.module.css"));
const LandingPageBuilder = lazy(
  () => import("../components/LandingPageBuilder/LandingPageBuilder"),
);

const ITMOcraft = () => {
  return (
    <FeatureGate
      flag="site_homepage_page_version"
      flag_type="variant"
      variants={{
        legacy: <ITMOcraftLegacy />,
        v2: (
          <>
            <LandingPageBuilder sections={itmocraftPageContent.sections} />
            <section className={sectionStyles.section}>
              <div className={`${sectionStyles.inner} ${styles.ctaInner}`}>
                <h1 className={styles.title}>
                  Остались вопросы? Смотри <a href="/joutak">наши гайды</a>
                </h1>
                <h2 className={styles.subtitle}>
                  Будем ждать тебя на нашем сервере!
                </h2>
                <MinecraftButton className={styles.ctaButton}>
                  зарегистрироваться
                </MinecraftButton>
              </div>
            </section>
          </>
        ),
      }}
      fallback={<ITMOcraftLegacy />}
    />
  );
};

export default ITMOcraft;
