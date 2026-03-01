import PropTypes from "prop-types";
import Carousel from "react-bootstrap/Carousel";

export default function ImageCarousel({ items, interval = 10000 }) {
  return (
    <div className="w-100" style={{ aspectRatio: "16 / 9" }}>
      <Carousel
        className="h-100"
        controls={items.length > 1}
        indicators={false}
        interval={interval}
      >
        {items.map((item) => (
          <Carousel.Item key={item.src} className="h-100">
            <img
              src={item.src}
              className="d-block w-100 h-100 object-fit-cover"
              alt={item.alt}
            />
          </Carousel.Item>
        ))}
      </Carousel>
    </div>
  );
}

ImageCarousel.propTypes = {
  items: PropTypes.arrayOf(
    PropTypes.shape({
      src: PropTypes.string.isRequired,
      alt: PropTypes.string.isRequired,
    }),
  ).isRequired,
  interval: PropTypes.number,
};
