import { bareClient, CLIENT_HEADERS } from "../http/client";
import {
  clearAuthStorage,
  mergeStoredTokens,
  readStoredTokens,
  tokenStore,
} from "./tokenStore";

export const ALLAUTH_APP_BASE = "auth/flow/app/v1";

export const HARD_LOGOUT_REASONS = Object.freeze({
  REFRESH_FAILED: "REFRESH_FAILED",
  SESSION_UNAUTHORIZED: "SESSION_UNAUTHORIZED",
});

let hardLogoutHandler = () => {};
let refreshPromise = null;

function isUnauthorized(error) {
  return error?.response?.status === 401;
}

function isRevokedSessionError(error) {
  return error?.response?.status === 410;
}

function isPendingMfaSession() {
  return readStoredTokens()?.pending_mfa === true;
}

export function extractSessionToken(respOrErrResp) {
  const meta = respOrErrResp?.data?.meta || {};
  return (
    meta.session_token || respOrErrResp?.headers?.["x-session-token"] || null
  );
}

export function setSessionToken(sessionToken, { emit = false } = {}) {
  if (!sessionToken) {
    return;
  }
  mergeStoredTokens({ session_token: sessionToken }, { emit });
}

export function buildSessionHeaders(sessionToken) {
  const accessToken = readStoredTokens()?.access || null;
  return {
    ...CLIENT_HEADERS,
    ...(sessionToken ? { "X-Session-Token": sessionToken } : {}),
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
  };
}

export function setupAxiosInterceptors(onHardLogout = () => {}) {
  hardLogoutHandler =
    typeof onHardLogout === "function" ? onHardLogout : () => {};
}

export function performHardLogout(
  reason = HARD_LOGOUT_REASONS.SESSION_UNAUTHORIZED,
) {
  clearAuthStorage({ emit: true });
  hardLogoutHandler?.({ reason });
}

export async function refreshAccessToken({ hardLogoutOnFailure = true } = {}) {
  if (!refreshPromise) {
    refreshPromise = bareClient
      .post(
        "/auth/refresh",
        {},
        { headers: buildSessionHeaders(tokenStore.getSessionToken()) },
      )
      .then(({ data }) => {
        const access = data?.access;

        if (!access) {
          throw new Error("Access token is missing in refresh response");
        }

        mergeStoredTokens({ access, refresh: null }, { emit: false });
        return { access };
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  try {
    return await refreshPromise;
  } catch (error) {
    if (hardLogoutOnFailure) {
      performHardLogout(HARD_LOGOUT_REASONS.REFRESH_FAILED);
    }
    throw error;
  }
}

export async function executeSessionRequest(
  method,
  url,
  { data = null, params, sessionToken, client = bareClient } = {},
) {
  const response = await client.request({
    method,
    url,
    data,
    params,
    headers: buildSessionHeaders(sessionToken),
  });

  const rotatedToken = extractSessionToken(response);
  if (rotatedToken && rotatedToken !== sessionToken) {
    setSessionToken(rotatedToken, { emit: false });
  }

  return response;
}

export async function requestWithSession(
  method,
  url,
  {
    data = null,
    params,
    rotateSessionTokenOn401 = true,
    refreshAccessOn401 = true,
    hardLogoutOn401 = true,
    client = bareClient,
  } = {},
) {
  const initialSessionToken = tokenStore.getSessionToken();
  let lastError = null;
  let refreshFailed = false;

  try {
    return await executeSessionRequest(method, url, {
      data,
      params,
      sessionToken: initialSessionToken,
      client,
    });
  } catch (error) {
    lastError = error;
  }

  if (!isUnauthorized(lastError)) {
    throw lastError;
  }

  if (isPendingMfaSession()) {
    if (rotateSessionTokenOn401) {
      const rotatedToken = extractSessionToken(lastError.response);
      if (rotatedToken && rotatedToken !== initialSessionToken) {
        setSessionToken(rotatedToken, { emit: false });
      }
    }
    throw lastError;
  }

  if (rotateSessionTokenOn401) {
    const rotatedToken = extractSessionToken(lastError.response);
    if (rotatedToken && rotatedToken !== initialSessionToken) {
      setSessionToken(rotatedToken, { emit: false });
      try {
        return await executeSessionRequest(method, url, {
          data,
          params,
          sessionToken: rotatedToken,
          client,
        });
      } catch (error) {
        lastError = error;
      }
    }
  }

  if (refreshAccessOn401 && isUnauthorized(lastError)) {
    let refreshed = false;
    try {
      await refreshAccessToken({ hardLogoutOnFailure: false });
      refreshed = true;
    } catch (error) {
      refreshFailed = true;
      lastError = error;
    }

    if (refreshed) {
      try {
        return await executeSessionRequest(method, url, {
          data,
          params,
          sessionToken: tokenStore.getSessionToken(),
          client,
        });
      } catch (error) {
        lastError = error;
      }
    }
  }

  if (hardLogoutOn401 && (refreshFailed || isUnauthorized(lastError))) {
    performHardLogout(
      refreshFailed
        ? HARD_LOGOUT_REASONS.REFRESH_FAILED
        : HARD_LOGOUT_REASONS.SESSION_UNAUTHORIZED,
    );
  }

  throw lastError;
}

export async function sessionGet(url, params, options = {}) {
  return requestWithSession("get", url, { ...options, params });
}

export async function sessionPost(url, data, options = {}) {
  return requestWithSession("post", url, { ...options, data });
}

export async function sessionPatch(url, data, options = {}) {
  return requestWithSession("patch", url, { ...options, data });
}

export async function sessionDelete(url, params, options = {}) {
  return requestWithSession("delete", url, { ...options, params });
}

export async function allauthAppRequest(
  method,
  url,
  { data = null, headers = {}, includeSession = true, params } = {},
) {
  try {
    const suffix = String(url || "").startsWith("/")
      ? String(url || "")
      : `/${String(url || "")}`;
    const requestHeaders = includeSession
      ? buildSessionHeaders(tokenStore.getSessionToken())
      : CLIENT_HEADERS;
    const response = await bareClient.request({
      method,
      url: `${ALLAUTH_APP_BASE}${suffix}`,
      data,
      params,
      headers: {
        ...requestHeaders,
        ...headers,
      },
    });

    const sessionToken = extractSessionToken(response);
    if (sessionToken) {
      setSessionToken(sessionToken, { emit: true });
    }

    return response;
  } catch (error) {
    const sessionToken = extractSessionToken(error?.response);
    if (sessionToken) {
      setSessionToken(sessionToken, { emit: true });
    }
    if (isRevokedSessionError(error)) {
      performHardLogout(HARD_LOGOUT_REASONS.SESSION_UNAUTHORIZED);
    }
    throw error;
  }
}
