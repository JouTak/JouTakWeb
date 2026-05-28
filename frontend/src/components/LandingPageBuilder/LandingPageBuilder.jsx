import MainSection from "../MainSection/MainSection";
import ProjectsSection from "../ProjectsSection/ProjectsSection";
import EventsSection from "../EventsSection/EventsSection";
import GallerySection from "../GallerySection/GallerySection";
import FAQsection from "../FAQsection/FAQsection";

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
          <SectionComponent
            key={section.key ?? `${section.type}-${index}`}
            {...(section.props ?? {})}
          />
        );
      })}
    </>
  );
}
