import axios from "axios";

export const BACKEND_URL = "__REACT_APP_API_URL__";

function stripTrailingSlash(value) {
  return String(value || "").replace(/\/+$/, "");
}

function normalizeBackendRoot(value) {
  const trimmed = stripTrailingSlash(value);
  return trimmed.endsWith("/api") ? trimmed.slice(0, -4) : trimmed;
}

export const BACKEND_ROOT_URL = normalizeBackendRoot(BACKEND_URL);
export const API_BASE = `${BACKEND_ROOT_URL}/api`;

export const CLIENT_HEADERS = Object.freeze({
  "X-Client": "app",
  "X-Allauth-Client": "app",
});

export const bareClient = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
});
