import PropTypes from "prop-types";
import { Link } from "react-router-dom";

import ImageCarousel from "../../components/ImageCarousel";

export default function LegacyHomepage({ content }) {
  const hero = content?.hero || {};
  const carousel = Array.isArray(content?.carousel) ? content.carousel : [];

  return (
    <div className="text-center">
      <ImageCarousel items={carousel} />

      <div className="p-5 mb-4 rounded-3">
        <div className="container pb-5">
          <h1 className="display-5 fw-bold">{hero.title || "JouTak"}</h1>
          <p className="col-md-8 fs-4 lh-xs mx-auto">{hero.description}</p>
          <p className="col-md-8 fs-4 lh-xs mx-auto fw-bold">
            IP: {hero.server_ip || "mc.joutak.ru"}
          </p>
          <a
            className="btn btn-primary btn-lg mt-4"
            href={hero.primary_cta?.href}
            target="_blank"
            rel="noopener noreferrer"
          >
            {hero.primary_cta?.label}
          </a>
          <br />
          <Link
            className="btn btn-primary btn-lg mt-3"
            to={hero.secondary_cta?.to || "/joutak/pay"}
          >
            {hero.secondary_cta?.label || "Оплатить проходку"}
          </Link>
        </div>
      </div>
    </div>
  );
}

LegacyHomepage.propTypes = {
  content: PropTypes.shape({
    hero: PropTypes.object,
    carousel: PropTypes.arrayOf(PropTypes.object),
  }),
};
