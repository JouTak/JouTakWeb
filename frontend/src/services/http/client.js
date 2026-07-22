import axios from "axios";

// Runtime placeholders substituted by `frontend/entrypoint.sh` at
// container boot. The `__JOUTAK_RUNTIME_*__` prefix is reserved for
// runtime injection — never hand-write such a string anywhere in the
// codebase, otherwise `sed` will replace it during image boot.
export const BACKEND_URL = "__JOUTAK_RUNTIME_API_URL__";
export const OTEL_TRACES_URL =
  "__JOUTAK_RUNTIME_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT__";
export const OTEL_SERVICE_NAME = "__JOUTAK_RUNTIME_OTEL_SERVICE_NAME__";

function stripTrailingSlash(value) {
  return String(value || "").replace(/\/+$/, "");
}

function normalizeOptionalRuntimeValue(value) {
  const raw = String(value || "").trim();
  if (!raw || (raw.startsWith("__JOUTAK_RUNTIME_") && raw.endsWith("__"))) {
    return "";
  }
  return raw;
}

function normalizeBackendRoot(value) {
  const trimmed = stripTrailingSlash(value);
  return trimmed.endsWith("/api") ? trimmed.slice(0, -4) : trimmed;
}

export const BACKEND_ROOT_URL = normalizeBackendRoot(BACKEND_URL);
export const API_BASE = `${BACKEND_ROOT_URL}/api`;
export const OTEL_EXPORTER_TRACES_URL =
  normalizeOptionalRuntimeValue(OTEL_TRACES_URL);
export const OTEL_RUNTIME_SERVICE_NAME =
  normalizeOptionalRuntimeValue(OTEL_SERVICE_NAME);

export const CLIENT_HEADERS = Object.freeze({
  "X-Client": "app",
  "X-Allauth-Client": "app",
});

export const bareClient = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
});

// Separate axios instance rooted at the backend host so that BFF
// endpoints (`/bff/*`) share the same session/refresh retry semantics
// as the Ninja-authored `/api/*` surface. Use this client via
// `requestWithSession(..., { client: rootClient })`.
export const rootClient = axios.create({
  baseURL: BACKEND_ROOT_URL,
  withCredentials: true,
});
