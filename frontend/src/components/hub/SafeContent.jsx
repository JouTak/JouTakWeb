import { useState } from "react";
import ReactMarkdown from "react-markdown";

import { safeExternalUrl, safeHubImageUrl } from "../../services/urlSafety";

export function ExternalLink({ href, children, className }) {
  const url = safeExternalUrl(href);
  return url ? (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={className}
    >
      {children}
    </a>
  ) : (
    <span>{children}</span>
  );
}
export function HubImage({ src, alt, cover = false }) {
  const [failed, setFailed] = useState(null);
  const safe = safeHubImageUrl(src);
  if (!safe || failed === safe)
    return cover ? null : (
      <span className="hub-avatar" aria-hidden="true">
        {alt?.slice(0, 1) || "J"}
      </span>
    );
  return (
    <img
      className={cover ? "hub-cover" : "hub-avatar"}
      src={safe}
      alt={alt}
      referrerPolicy="no-referrer"
      onError={() => setFailed(safe)}
    />
  );
}
export function Markdown({ children }) {
  return (
    <div className="hub-markdown">
      <ReactMarkdown
        skipHtml
        components={{
          a: ({ href, children }) => (
            <ExternalLink href={href}>{children}</ExternalLink>
          ),
          img: ({ alt }) => <span>{alt}</span>,
        }}
      >
        {children || "Описание пока не добавлено."}
      </ReactMarkdown>
    </div>
  );
}
