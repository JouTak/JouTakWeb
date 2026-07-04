import LandingPageBuilder from "../components/LandingPageBuilder/LandingPageBuilder";
import MinecraftButton from "../components/MinecraftButton/MinecraftButton";
import sectionStyles from "../components/shared/sectionLayout.module.css";
import FeatureGate from "../features/featureFlags/FeatureGate";
import LegacyItmocraft from "../Legacy/frontend/src/pages/JouTak"
import styles from "./ItmoCraft.module.css";
import { itmoCraftPageContent } from "./landingContent";

const ItmoCraft = () => {
  return (
    <>
      <FeatureGate
      flag="site_new_itmocraft_page"
      fallback={<LegacyItmocraft />}
      >
      <LandingPageBuilder sections={itmoCraftPageContent.sections} />
      <section className={sectionStyles.section}>
        <div className={`${sectionStyles.inner} ${styles.ctaInner}`}>
          <h1 className={styles.title}>
            Остались вопросы? Смотри <a href="/joutak">наши гайды</a>
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
