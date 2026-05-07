import PropTypes from "prop-types";
import { Link } from "react-router-dom";

function Hero({ hero }) {
  return (
    <section className="rounded-4 p-4 p-lg-5 text-light mb-4 bg-dark">
      <div className="row g-4 align-items-center">
        <div className="col-lg-8">
          <div className="text-uppercase small text-warning mb-2">
            {hero?.eyebrow || "JouTak Community"}
          </div>
          <h1 className="display-4 fw-bold mb-3">{hero?.title}</h1>
          <p className="fs-5 text-secondary mb-4">{hero?.description}</p>
          <div className="d-flex flex-wrap gap-3 align-items-center">
            <a
              className="btn btn-warning btn-lg"
              href={hero?.primary_cta?.href}
              target="_blank"
              rel="noopener noreferrer"
            >
              {hero?.primary_cta?.label}
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
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="h3 mb-0">Наши проекты</h2>
        <span className="text-secondary">Feature-gated v2</span>
      </div>
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

function FAQ({ items }) {
  return (
    <section className="mb-4">
      <h2 className="h3 mb-3">FAQ</h2>
      <div className="accordion" id="homepageFaq">
        {items.map((item, index) => (
          <div key={item.question} className="accordion-item">
            <h3 className="accordion-header">
              <button
                className={`accordion-button ${index > 0 ? "collapsed" : ""}`}
                type="button"
                data-bs-toggle="collapse"
                data-bs-target={`#faq-${index}`}
                aria-expanded={index === 0 ? "true" : "false"}
                aria-controls={`faq-${index}`}
              >
                {item.question}
              </button>
            </h3>
            <div
              id={`faq-${index}`}
              className={`accordion-collapse collapse ${index === 0 ? "show" : ""}`}
              data-bs-parent="#homepageFaq"
            >
              <div className="accordion-body">{item.answer}</div>
            </div>
          </div>
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
      <Projects
        items={Array.isArray(content?.projects) ? content.projects : []}
      />
      <Events items={Array.isArray(content?.events) ? content.events : []} />
      <Gallery items={Array.isArray(content?.gallery) ? content.gallery : []} />
      <FAQ items={Array.isArray(content?.faq) ? content.faq : []} />
    </div>
  );
}

HomepageV2.propTypes = {
  content: PropTypes.object,
};
