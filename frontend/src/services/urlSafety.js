import { BACKEND_ROOT_URL } from "./http/client";

export function isSafeInternalPath(path) {
  return (
    typeof path === "string" &&
    path.startsWith("/") &&
    !path.startsWith("//") &&
    !path.includes("\\") &&
    !Array.from(path).some((character) => {
      const code = character.charCodeAt(0);
      return code <= 32 || code === 127;
    })
  );
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
  if (isSafeInternalPath(s)) {
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
