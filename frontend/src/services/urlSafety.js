import { BACKEND_ROOT_URL } from "./http/client";

export function sanitizeUrl(u) {
  if (typeof u !== "string") return "";
  const s = u.trim();
  if (/^(javascript|data):/i.test(s)) return "";
  const base = BACKEND_ROOT_URL;
  const currentOrigin =
    typeof window === "undefined" ? null : window.location?.origin;
  if (s.startsWith("/") && !s.startsWith("//")) {
    return `${base}${s}`;
  }

  try {
    const parsed = new URL(s);
    const backendOrigin = new URL(base).origin;
    const allowedOrigins = new Set(
      [backendOrigin, currentOrigin].filter(Boolean),
    );
    if (allowedOrigins.has(parsed.origin)) {
      return parsed.toString();
    }
  } catch {
    return "";
  }

  return "";
}
