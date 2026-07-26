import PropTypes from "prop-types";

import { getMediaDescriptor } from "./mediaResolver";

export default function ResponsiveMedia({
  media,
  alt,
  className,
  pictureClassName,
  eager = false,
  sizes = "100vw",
}) {
  const descriptor = getMediaDescriptor(media);
  if (!descriptor) return null;
  const srcSet = descriptor.sources
    .map((source) => `${source.src} ${source.width}w`)
    .join(", ");

  return (
    <picture
      className={pictureClassName}
      data-design-placeholder={descriptor.designPlaceholder || undefined}
    >
      {srcSet && <source type="image/webp" srcSet={srcSet} sizes={sizes} />}
      <img
        className={className}
        src={descriptor.src}
        alt={alt ?? media?.alt ?? ""}
        width={descriptor.width}
        height={descriptor.height}
        loading={eager ? "eager" : "lazy"}
        fetchPriority={eager ? "high" : "auto"}
        decoding="async"
      />
    </picture>
  );
}

ResponsiveMedia.propTypes = {
  media: PropTypes.object,
  alt: PropTypes.string,
  className: PropTypes.string,
  pictureClassName: PropTypes.string,
  eager: PropTypes.bool,
  sizes: PropTypes.string,
};
