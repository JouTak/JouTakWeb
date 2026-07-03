import LandingPageBuilder from "../components/LandingPageBuilder/LandingPageBuilder";
import { itmoCraftPageContent } from "./landingContent";
import MinecraftButton from "../components/MineCraftButton/MinecraftButton";
import sectionStyles from "../components/shared/sectionLayout.module.css";
import styles from "./ItmoCraft.module.css";
import FeatureGate from "../features/featureFlags/FeatureGate";
import LegacyHomepage from "../Legacy/frontend/src/pages/Joutak"

const ItmoCraft = () => {
  return (
    <>
      <FeatureGate
      flag="site_new_homepage"
      fallback={<LegacyHomepage />}
      >
      <LandingPageBuilder sections={itmoCraftPageContent.sections} />
      <section className={sectionStyles.section}>
        <div className={`${sectionStyles.inner} ${styles.ctaInner}`}>
          <h1 className={styles.title}>
            Остались вопросы? Смотри <a href="#">наши гайды</a>
          </h1>
          <h2 className={styles.subtitle}>Будем ждать тебя на нашем сервере!</h2>
          <MinecraftButton className={styles.ctaButton}>зарегистрироваться</MinecraftButton>
        </div>
      </section>
      </FeatureGate>
    </>
  );
};

export default ItmoCraft;
