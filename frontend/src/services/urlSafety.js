import { BACKEND_ROOT_URL } from "./http/client";

// User-authored external content has a different policy from OAuth redirects.
export function safeExternalUrl(value) {
  if (typeof value !== "string" || /[\\\s]/.test(value)) return "";
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password
      ? url.href
      : "";
  } catch {
    return "";
  }
}

export function safeHubImageUrl(value) {
  return /^\/media\/hub\/[a-f0-9]{32}\.webp$/.test(value || "")
    ? `${BACKEND_ROOT_URL}${value}`
    : safeExternalUrl(value);
}

// NB: previously we also allowed `window.location.origin` as a safe
// target. That created an open-redirect vector if the SPA was ever
// served from an attacker-controlled origin (e.g. subdomain takeover).
// We now only accept the configured backend origin plus same-origin
// absolute paths.
export function sanitizeUrl(u) {
  if (typeof u !== "string") return "";
  const s = u.trim();
  if (!s) return "";
  if (/^(javascript|data|vbscript):/i.test(s)) return "";
  const base = BACKEND_ROOT_URL;
  if (s.startsWith("/") && !s.startsWith("//")) {
    return `${base}${s}`;
  }

  try {
    const parsed = new URL(s);
    const backendOrigin = new URL(base).origin;
    if (parsed.origin === backendOrigin) {
      return parsed.toString();
    }
  } catch {
    return "";
  }

  return "";
}

// Navigation after authentication must remain in this SPA, including query/hash.
export function safeInternalPath(value, fallback = "/joutak") {
  if (
    typeof value !== "string" ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    /[\\\s]/.test(value)
  )
    return fallback;
  try {
    const decoded = decodeURIComponent(value);
    if (
      decoded.startsWith("//") ||
      decoded.includes("\\") ||
      [...decoded].some((char) => char.charCodeAt(0) <= 32)
    )
      return fallback;
    const parsed = new URL(value, "https://joutak.invalid");
    if (
      parsed.origin !== "https://joutak.invalid" ||
      ["/login", "/session-expired"].includes(parsed.pathname)
    )
      return fallback;
    return parsed.pathname + parsed.search + parsed.hash;
  } catch {
    return fallback;
  }
}
