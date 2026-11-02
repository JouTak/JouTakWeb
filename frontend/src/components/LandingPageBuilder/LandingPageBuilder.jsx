import PropTypes from "prop-types";

import { resolveAction } from "../../media/mediaResolver";
import EventsSection from "../EventsSection/EventsSection";
import FAQSection from "../FAQSection/FAQSection";
import GallerySection from "../GallerySection/GallerySection";
import MainSection from "../MainSection/MainSection";
import ProductActionsSection from "../ProductActionsSection/ProductActionsSection";
import ProjectsSection from "../ProjectsSection/ProjectsSection";

function sectionProps(section) {
  if (section.type === "hero") {
    return {
      backgroundMedia: section.background,
      logoMedia: section.logo,
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
        imageMedia: item.image,
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
        imageMedia: item.image,
        date: new Date(item.starts_at),
        to: resolveAction(item.action),
        actionLabel: item.action_label,
        actionDisabled: item.action.kind === "design_placeholder",
      })),
    };
  }
  if (section.type === "actions") {
    return {
      eyebrow: section.eyebrow,
      title: section.title,
      description: section.description,
      facts: section.facts,
      items: section.items.map((item) => ({
        id: item.id,
        label: item.label,
        emphasis: item.emphasis,
        href: resolveAction(item.action),
        external: item.action.kind === "external",
        disabled: item.action.kind === "design_placeholder",
      })),
    };
  }
  if (section.type === "gallery") {
    return {
      title: section.title,
      galleryItems: section.items.map((item) => ({
        label: item.label,
        image: item.cover,
        photos: item.photos,
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
  actions: ProductActionsSection,
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
