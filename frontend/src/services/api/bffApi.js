import { requestWithSession } from "../auth/sessionClient";
import { rootClient } from "../http/client";

export function pickFeatureOverrideParams(search) {
  const params = new URLSearchParams(search || "");
  const filtered = new URLSearchParams();

  for (const [key, value] of params.entries()) {
    if (key.startsWith("ff_") || key === "ff_clear_overrides") {
      filtered.set(key, value);
    }
  }

  return filtered;
}

async function bffGet(url, params) {
  // Re-use `requestWithSession` so BFF endpoints share the same 401
  // rotation/refresh/hard-logout flow as Ninja endpoints. `client` is
  // the backend-root axios instance so relative URLs resolve against
  // the backend host, not the `/api` prefix.
  const response = await requestWithSession("get", url, {
    params,
    client: rootClient,
    // BFF requests are happy to fall back to an anonymous view when
    // nothing authenticates, so we don't want a 401 here to forcibly
    // log the user out.
    hardLogoutOn401: false,
  });
  return response.data;
}

export async function getBootstrap(params) {
  return bffGet("/bff/bootstrap", params);
}

export async function getHomepagePayload(params) {
  return bffGet("/bff/pages/home", params);
}

export async function getAccountSummary(params) {
  return bffGet("/bff/account/summary", params);
}
