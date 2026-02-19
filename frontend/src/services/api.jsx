import axios from "axios";

export const BACKEND_URL = "__REACT_APP_API_URL__";
const API_BASE = `${BACKEND_URL.replace(/\/$/, "")}/api`;
const TOKENS_KEY = "joutak_auth";
export const AUTH_STATE_EVENT = "joutak:auth-state-changed";

const CLIENT_HEADERS = Object.freeze({
  "X-Client": "app",
  "X-Allauth-Client": "app",
});

const HARD_LOGOUT_REASONS = Object.freeze({
  MISSING_REFRESH: "MISSING_REFRESH",
  REFRESH_FAILED: "REFRESH_FAILED",
  SESSION_UNAUTHORIZED: "SESSION_UNAUTHORIZED",
});

const bareClient = axios.create({ baseURL: API_BASE });

let hardLogoutHandler = () => {};
let refreshPromise = null;

function hasAuthTokens(tokens) {
  return Boolean(tokens?.session_token || tokens?.access || tokens?.refresh);
}

function emitAuthStateChanged() {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new Event(AUTH_STATE_EVENT));
}

function readStoredTokens() {
  try {
    return JSON.parse(localStorage.getItem(TOKENS_KEY) || "{}");
  } catch {
    return {};
  }
}

function writeStoredTokens(tokens, { emit = true } = {}) {
  const previousTokens = readStoredTokens();
  const nextTokens = tokens && typeof tokens === "object" ? tokens : {};

  if (Object.keys(nextTokens).length === 0) {
    localStorage.removeItem(TOKENS_KEY);
  } else {
    localStorage.setItem(TOKENS_KEY, JSON.stringify(nextTokens));
  }

  if (emit) {
    const previousState = hasAuthTokens(previousTokens);
    const nextState = hasAuthTokens(nextTokens);
    if (previousState !== nextState) {
      emitAuthStateChanged();
    }
  }
}

function mergeStoredTokens(partial, { emit = true } = {}) {
  const currentTokens = readStoredTokens();
  writeStoredTokens({ ...currentTokens, ...(partial || {}) }, { emit });
}

function isUnauthorized(error) {
  return error?.response?.status === 401;
}

function extractSessionToken(respOrErrResp) {
  const meta = respOrErrResp?.data?.meta || {};
  return meta.session_token || respOrErrResp?.headers?.["x-session-token"] || null;
}

function setSessionToken(sessionToken, { emit = false } = {}) {
  if (!sessionToken) {
    return;
  }
  mergeStoredTokens({ session_token: sessionToken }, { emit });
}

function buildSessionHeaders(sessionToken) {
  const accessToken = readStoredTokens()?.access || null;
  return {
    ...CLIENT_HEADERS,
    ...(sessionToken ? { "X-Session-Token": sessionToken } : {}),
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
  };
}

function clearAuthStorage({ emit = true } = {}) {
  writeStoredTokens({}, { emit });
}

function performHardLogout(reason = HARD_LOGOUT_REASONS.SESSION_UNAUTHORIZED) {
  clearAuthStorage({ emit: true });
  hardLogoutHandler?.({ reason });
}

async function refreshAccessToken({ hardLogoutOnFailure = true } = {}) {
  const refreshToken = readStoredTokens()?.refresh || null;

  if (!refreshToken) {
    const error = new Error("Refresh token is missing");
    error.code = HARD_LOGOUT_REASONS.MISSING_REFRESH;
    if (hardLogoutOnFailure) {
      performHardLogout(HARD_LOGOUT_REASONS.MISSING_REFRESH);
    }
    throw error;
  }

  if (!refreshPromise) {
    refreshPromise = bareClient
      .post(
        "/auth/refresh",
        { refresh: refreshToken },
        { headers: buildSessionHeaders(tokenStore.getSessionToken()) },
      )
      .then(({ data }) => {
        const access = data?.access;
        const refresh = data?.refresh || refreshToken;

        if (!access) {
          throw new Error("Access token is missing in refresh response");
        }

        mergeStoredTokens({ access, refresh }, { emit: false });
        return { access, refresh };
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

function sanitizeUrl(u) {
  if (typeof u !== "string") return "";
  const s = u.trim();
  if (/^https?:\/\//i.test(s)) return s;
  if (/^\/\//.test(s)) return "https:" + s;
  if (/^(javascript|data):/i.test(s)) return "";
  const base = BACKEND_URL.replace(/\/$/, "");
  const path = s.startsWith("/") ? s : `/${s}`;
  return `${base}${path}`;
}

async function executeSessionRequest(method, url, { data = null, params, sessionToken } = {}) {
  const response = await bareClient.request({
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

async function requestWithSession(
  method,
  url,
  {
    data = null,
    params,
    rotateSessionTokenOn401 = true,
    refreshAccessOn401 = true,
    hardLogoutOn401 = true,
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
    });
  } catch (error) {
    lastError = error;
  }

  if (!isUnauthorized(lastError)) {
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

async function sessionGet(url, params, options = {}) {
  return requestWithSession("get", url, { ...options, params });
}

async function sessionPost(url, data, options = {}) {
  return requestWithSession("post", url, { ...options, data });
}

async function sessionPatch(url, data, options = {}) {
  return requestWithSession("patch", url, { ...options, data });
}

async function sessionDelete(url, params, options = {}) {
  return requestWithSession("delete", url, { ...options, params });
}

export function setupAxiosInterceptors(onHardLogout = () => {}) {
  hardLogoutHandler = typeof onHardLogout === "function" ? onHardLogout : () => {};
}

export const tokenStore = {
  get() {
    return readStoredTokens();
  },
  set(tokens) {
    writeStoredTokens(tokens, { emit: true });
  },
  clear() {
    clearAuthStorage({ emit: true });
  },
  getSessionToken() {
    return readStoredTokens()?.session_token || null;
  },
};

export function hasStoredAuth() {
  return hasAuthTokens(readStoredTokens());
}

export function clearAuthState() {
  clearAuthStorage({ emit: true });
}

export async function loginApp({ username, password }) {
  const { data, headers } = await bareClient.post("/auth/login", {
    username: String(username || "").trim(),
    password,
  });

  const sessionToken = extractSessionToken({ data, headers });
  if (!sessionToken) {
    throw new Error("No session token returned on login");
  }

  setSessionToken(sessionToken, { emit: true });
  return sessionToken;
}

export async function signupApp({ username, email, password }) {
  const body = {
    username: String(username || "").trim(),
    email: String(email || "").trim(),
    password,
  };

  const { data, headers } = await bareClient.post("/auth/signup", body);
  const sessionToken = extractSessionToken({ data, headers });

  if (!sessionToken) {
    throw new Error("No session token returned on signup");
  }

  setSessionToken(sessionToken, { emit: true });
  return sessionToken;
}

export async function jwtFromSession() {
  const response = await sessionPost("/auth/jwt/from_session", null, {
    hardLogoutOn401: false,
    refreshAccessOn401: false,
  });

  const pair = response.data;
  mergeStoredTokens(
    {
      access: pair?.access || null,
      refresh: pair?.refresh || null,
    },
    { emit: false },
  );
  return pair;
}

export async function doLogin({ username, password }) {
  await loginApp({ username, password });
  try {
    await jwtFromSession();
  } catch {
    // Session can still be valid for headless endpoints even if JWT exchange fails.
  }
  return tokenStore.get();
}

export async function doSignupAndLogin({ username, email, password }) {
  await signupApp({ username, email, password });
  try {
    await jwtFromSession();
  } catch {
    // Session can still be valid for headless endpoints even if JWT exchange fails.
  }
  return tokenStore.get();
}

export async function logout() {
  try {
    await sessionPost("/auth/logout", null, {
      hardLogoutOn401: false,
      refreshAccessOn401: false,
    });
  } finally {
    clearAuthStorage({ emit: true });
  }
}

export async function me() {
  const { data } = await sessionGet("/auth/me");
  return data;
}

export async function changePassword({ current_password, new_password }) {
  const { data } = await sessionPost("/auth/change_password", {
    current_password,
    new_password,
  });
  return data;
}

export async function getOAuthProviders() {
  const { data } = await sessionGet("/oauth/providers");
  return data?.providers || [];
}

export async function getOAuthLink(provider, next = "/account/security#linked") {
  const { data } = await sessionGet(`/oauth/link/${provider}`, { next });
  return {
    url: sanitizeUrl(data?.authorize_url),
    method: data?.method || "POST",
  };
}

export async function listSessionsHeadless() {
  const { data } = await sessionGet("/account/sessions");
  return data;
}

export async function revokeSessionHeadless(session_id, reason = "manual") {
  const response = await sessionDelete(
    `/account/sessions/${encodeURIComponent(session_id)}`,
    { reason },
  );
  return response.data;
}

export async function bulkRevokeSessionsHeadless() {
  const { data } = await sessionPost("/account/sessions/_bulk", {
    all_except_current: true,
    reason: "bulk_except_current",
  });
  return data;
}

export async function getEmailStatus() {
  const { data } = await sessionGet("/account/email");
  return data;
}

export async function changeEmail(new_email) {
  const { data } = await sessionPost("/account/email/change", { new_email });
  return data;
}

export async function resendEmailVerification() {
  const { data } = await sessionPost("/account/email/resend", null);
  return data;
}

export async function getAccountStatus() {
  const { data } = await sessionGet("/account/status");
  return data;
}

export async function deleteCurrentAccount(current_password) {
  const { data } = await sessionPost("/account/delete", { current_password });
  return data;
}

export async function updateProfile(payload = {}) {
  const {
    first_name,
    last_name,
    vk_username,
    minecraft_nick,
    minecraft_has_license,
    is_itmo_student,
    itmo_isu,
  } = payload;

  const { data } = await sessionPatch("/account/profile", {
    ...(first_name !== undefined ? { first_name } : {}),
    ...(last_name !== undefined ? { last_name } : {}),
    ...(vk_username !== undefined ? { vk_username } : {}),
    ...(minecraft_nick !== undefined ? { minecraft_nick } : {}),
    ...(minecraft_has_license !== undefined ? { minecraft_has_license } : {}),
    ...(is_itmo_student !== undefined ? { is_itmo_student } : {}),
    ...(itmo_isu !== undefined ? { itmo_isu } : {}),
  });

  return data;
}
