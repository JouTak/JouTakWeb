import FeatureGate from "../../features/featureFlags/FeatureGate";
import EventsSection from "../EventsSection/EventsSection";
import FAQsection from "../FAQSection/FAQsection";
import GallerySection from "../GallerySection/GallerySection";
import MainSection from "../MainSection/MainSection";
import ProjectsSection from "../ProjectsSection/ProjectsSection";

const SECTION_COMPONENTS = {
  main: MainSection,
  projects: ProjectsSection,
  events: EventsSection,
  gallery: GallerySection,
  faq: FAQsection,
};

export default function LandingPageBuilder({ sections = [] }) {
  return (
    <>
      {sections.map((section, index) => {
        const SectionComponent = SECTION_COMPONENTS[section.type];

        if (!SectionComponent) {
          return null;
        }

        return (
          <FeatureGate
            key={section.key ?? `${section.type}-${index}`}
            flag={section.flag ?? "site_new_homepage"}
          >
            <SectionComponent {...(section.props ?? {})} />
          </FeatureGate>
        );
      })}
    </>
  );
}
