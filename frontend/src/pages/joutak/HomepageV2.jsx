import PropTypes from "prop-types";
import { useState } from "react";
import { Link } from "react-router-dom";

import EventsSection from "../../components/EventsSection/EventsSection.jsx";
import FAQSection from "../../components/FAQSection/FAQSection.jsx";
import GallerySection from "../../components/GallerySection/GallerySection.jsx";
import ProjectsSection from "../../components/ProjectsSection/ProjectsSection.jsx";
import FeatureGate from "../../features/featureFlags/FeatureGate.jsx";

function Hero({ hero }) {
  return (
    <section className="rounded-4 p-4 p-lg-5 text-light mb-4 bg-dark">
      <div className="row g-4 align-items-center">
        <div className="col-lg-8">
          <div className="text-uppercase small text-warning mb-2">
            {hero?.eyebrow || "JouTak Community"}
          </div>
          <h1 className="display-4 fw-bold mb-3">{hero?.title || "JouTak"}</h1>
          <p className="fs-5 text-secondary mb-4">
            {hero?.description ||
              "Интерфейс доступен без backend. API-зависимые действия будут недоступны, пока бэкенд не поднят."}
          </p>
          <div className="d-flex flex-wrap gap-3 align-items-center">
            <a
              className="btn btn-warning btn-lg"
              href={hero?.primary_cta?.href || "https://joutak.ru"}
              target="_blank"
              rel="noopener noreferrer"
            >
              {hero?.primary_cta?.label || "Открыть JouTak"}
            </a>
            <Link
              className="btn btn-outline-light btn-lg"
              to={hero?.secondary_cta?.to || "/joutak/pay"}
            >
              {hero?.secondary_cta?.label || "Оплатить проходку"}
            </Link>
            <span className="badge text-bg-light fs-6">
              IP: {hero?.server_ip || "mc.joutak.ru"}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

Hero.propTypes = {
  hero: PropTypes.object,
};

function Projects({ items }) {
  return (
    <section className="mb-4">
      <h2 className="h3 mb-3">Наши проекты</h2>
      <div className="row g-3">
        {items.map((item) => (
          <div key={item.title} className="col-md-6 col-xl-3">
            <div className="h-100 border rounded-4 p-4 bg-body-tertiary">
              <h3 className="h5">{item.title}</h3>
              <p className="text-secondary">{item.description}</p>
              <Link className="btn btn-sm btn-outline-primary" to={item.path}>
                Перейти
              </Link>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

Projects.propTypes = {
  items: PropTypes.arrayOf(PropTypes.object).isRequired,
};

function Events({ items }) {
  return (
    <section className="mb-4">
      <h2 className="h3 mb-3">Что происходит в сообществе</h2>
      <div className="row g-3">
        {items.map((item) => (
          <div key={item} className="col-md-4">
            <div className="border rounded-4 p-4 h-100 bg-body-tertiary">
              {item}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

Events.propTypes = {
  items: PropTypes.arrayOf(PropTypes.string).isRequired,
};

function Gallery({ items }) {
  return (
    <section className="mb-4">
      <h2 className="h3 mb-3">Галерея</h2>
      <div className="row g-3">
        {items.map((item) => (
          <div key={item} className="col-md-4">
            <img
              className="img-fluid rounded-4 border"
              src={item}
              alt="JouTak gallery"
              loading="lazy"
            />
          </div>
        ))}
      </div>
    </section>
  );
}

Gallery.propTypes = {
  items: PropTypes.arrayOf(PropTypes.string).isRequired,
};

function FaqItem({ item, isOpen, onToggle }) {
  return (
    <div className="accordion-item">
      <h3 className="accordion-header">
        <button
          className={`accordion-button ${isOpen ? "" : "collapsed"}`}
          type="button"
          onClick={onToggle}
          aria-expanded={isOpen}
        >
          {item.question}
        </button>
      </h3>
      <div className={`accordion-collapse collapse ${isOpen ? "show" : ""}`}>
        <div className="accordion-body">{item.answer}</div>
      </div>
    </div>
  );
}

FaqItem.propTypes = {
  item: PropTypes.object.isRequired,
  isOpen: PropTypes.bool.isRequired,
  onToggle: PropTypes.func.isRequired,
};

function FAQ({ items }) {
  const [openIndex, setOpenIndex] = useState(0);

  return (
    <section className="mb-4">
      <h2 className="h3 mb-3">FAQ</h2>
      <div className="accordion">
        {items.map((item, index) => (
          <FaqItem
            key={item.question}
            item={item}
            isOpen={openIndex === index}
            onToggle={() => setOpenIndex(openIndex === index ? -1 : index)}
          />
        ))}
      </div>
    </section>
  );
}

FAQ.propTypes = {
  items: PropTypes.arrayOf(PropTypes.object).isRequired,
};

export default function HomepageV2({ content }) {
  return (
    <div className="py-2">
      <Hero hero={content?.hero} />
      <FeatureGate
        flag="joutak_projects_section"
        fallback={
          <Projects
            items={Array.isArray(content?.projects) ? content.projects : []}
          />
        }
      >
        <ProjectsSection
          items={Array.isArray(content?.projects) ? content.projects : []}
        />
      </FeatureGate>
      <FeatureGate
        flag="joutak_events_section"
        fallback={
          <Events items={Array.isArray(content?.events) ? content.events : []} />
        }
      >
        <EventsSection
          items={Array.isArray(content?.events) ? content.events : []}
        />
      </FeatureGate>
      <FeatureGate
        flag="joutak_gallery_section"
        fallback={
          <Gallery
            items={Array.isArray(content?.gallery) ? content.gallery : []}
          />
        }
      >
        <GallerySection
          items={Array.isArray(content?.gallery) ? content.gallery : []}
        />
      </FeatureGate>
      <FeatureGate
        flag="joutak_faq_section"
        fallback={
          <FAQ items={Array.isArray(content?.faq) ? content.faq : []} />
        }
      >
        <FAQSection
          items={Array.isArray(content?.faq) ? content.faq : []}
        />
      </FeatureGate>
    </div>
  );
}

HomepageV2.propTypes = {
  content: PropTypes.object,
};
