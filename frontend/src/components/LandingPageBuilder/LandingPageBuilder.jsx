import PropTypes from "prop-types";

import { resolveAction, resolveMedia } from "../../media/mediaResolver";
import EventsSection from "../EventsSection/EventsSection";
import FAQSection from "../FAQSection/FAQSection";
import GallerySection from "../GallerySection/GallerySection";
import MainSection from "../MainSection/MainSection";
import ProjectsSection from "../ProjectsSection/ProjectsSection";

function sectionProps(section) {
  if (section.type === "hero") {
    return {
      backgroundImage: resolveMedia(section.background),
      logoSrc: resolveMedia(section.logo),
      logoAlt: section.logo?.alt || section.title,
      notificationUpperText: section.eyebrow || section.title,
      notificationLowerText: section.description || section.title,
    };
  }
  if (section.type === "projects") {
    return {
      title: section.title,
      projects: section.items.map((item) => ({
        title: item.title,
        description: item.description,
        image: resolveMedia(item.image),
        to: resolveAction(item.action),
      })),
    };
  }
  if (section.type === "events") {
    return {
      title: section.title,
      events: section.items.map((item) => ({
        title: item.title,
        description: item.description,
        location: item.location,
        image: resolveMedia(item.image),
        date: new Date(item.starts_at),
        to: resolveAction(item.action),
      })),
    };
  }
  if (section.type === "gallery") {
    return {
      title: section.title,
      galleryItems: section.items.map((item) => ({
        label: item.label,
        image: resolveMedia(item.cover),
        photos: item.photos.map(resolveMedia),
      })),
    };
  }
  return {
    title: section.title,
    faqItems: section.items,
  };
}

const SECTION_COMPONENTS = {
  hero: MainSection,
  projects: ProjectsSection,
  events: EventsSection,
  gallery: GallerySection,
  faq: FAQSection,
};

export default function LandingPageBuilder({ sections = [] }) {
  return (
    <>
      {sections.map((section, index) => {
        const SectionComponent = SECTION_COMPONENTS[section.type];
        if (!SectionComponent) return null;
        const containsPlaceholder = JSON.stringify(section).includes(
          '"design_placeholder"',
        );
        return (
          <div
            key={section.id ?? `${section.type}-${index}`}
            data-design-placeholder={containsPlaceholder ? "true" : undefined}
          >
            <SectionComponent {...sectionProps(section)} />
          </div>
        );
      })}
    </>
  );
}

LandingPageBuilder.propTypes = {
  sections: PropTypes.arrayOf(PropTypes.object),
};
