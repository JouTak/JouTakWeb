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
const API_BASE = `${BACKEND_ROOT_URL}/api`;
const ALLAUTH_APP_BASE = "/auth/flow/app/v1";
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

function isRevokedSessionError(error) {
  return error?.response?.status === 410;
}

function extractSessionToken(respOrErrResp) {
  const meta = respOrErrResp?.data?.meta || {};
  return (
    meta.session_token || respOrErrResp?.headers?.["x-session-token"] || null
  );
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
  const base = BACKEND_ROOT_URL;
  const path = s.startsWith("/") ? s : `/${s}`;
  return `${base}${path}`;
}

async function executeSessionRequest(
  method,
  url,
  { data = null, params, sessionToken } = {},
) {
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

async function allauthAppRequest(
  method,
  url,
  { data = null, headers = {} } = {},
) {
  try {
    const sessionHeaders = buildSessionHeaders(tokenStore.getSessionToken());
    const response = await bareClient.request({
      method,
      url: `${ALLAUTH_APP_BASE}${url}`,
      data,
      headers: {
        ...sessionHeaders,
        ...headers,
      },
    });

    const sessionToken = extractSessionToken(response);
    if (sessionToken) {
      setSessionToken(sessionToken, { emit: true });
    }

    return response;
  } catch (error) {
    if (isRevokedSessionError(error)) {
      performHardLogout(HARD_LOGOUT_REASONS.SESSION_UNAUTHORIZED);
    }
    throw error;
  }
}

function normalizeEmailStatus(addresses) {
  const items = Array.isArray(addresses) ? addresses : [];
  const primary = items.find((item) => item?.primary) || items[0] || null;
  const pending =
    items.find((item) => item && !item.primary && !item.verified) || null;
  const resendTarget =
    pending?.email ||
    (primary && !primary.verified ? primary.email : null) ||
    null;

  return {
    email: primary?.email || "",
    verified: !!primary?.verified,
    pending_email: pending?.email || null,
    resend_target: resendTarget,
    addresses: items,
  };
}

function getAnonymousCompletionPayload(error) {
  const response = error?.response;
  const payload = response?.data;
  if (response?.status !== 401 || !payload || payload.errors) {
    return null;
  }
  if (payload?.meta?.is_authenticated !== false) {
    return null;
  }
  if (!Array.isArray(payload?.data?.flows)) {
    return null;
  }
  return payload;
}

export function setupAxiosInterceptors(onHardLogout = () => {}) {
  hardLogoutHandler =
    typeof onHardLogout === "function" ? onHardLogout : () => {};
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

export async function loginApp({ login, password }) {
  const response = await allauthAppRequest("post", "/auth/login", {
    data: {
      username: String(login || "").trim(),
      password,
    },
  });

  const sessionToken = extractSessionToken(response);
  if (!sessionToken) {
    throw new Error("No session token returned on login");
  }

  setSessionToken(sessionToken, { emit: true });
  return sessionToken;
}

export async function signupApp({ email, password }) {
  const response = await allauthAppRequest("post", "/auth/signup", {
    data: {
      email: String(email || "").trim(),
      password,
    },
  });

  const sessionToken = extractSessionToken(response);
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

export async function doLogin({ login, password }) {
  await loginApp({ login, password });
  try {
    await jwtFromSession();
  } catch {
    // Session can still be valid for headless endpoints even if JWT exchange fails.
  }
  return tokenStore.get();
}

export async function doSignupAndLogin({ email, password }) {
  await signupApp({ email, password });
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

export async function changePassword({
  current_password,
  new_password,
  logout_current_session = false,
}) {
  const { data } = await sessionPost("/auth/change_password", {
    current_password,
    new_password,
    logout_current_session,
  });
  if (data?.logged_out_current_session) {
    clearAuthStorage({ emit: true });
  }
  return data;
}

export async function inspectEmailVerification(key) {
  const { data } = await allauthAppRequest("get", "/auth/email/verify", {
    headers: { "X-Email-Verification-Key": key },
  });
  return data;
}

export async function confirmEmailVerification(key) {
  try {
    const { data } = await allauthAppRequest("post", "/auth/email/verify", {
      data: { key },
      headers: { "X-Email-Verification-Key": key },
    });
    return data;
  } catch (error) {
    const completion = getAnonymousCompletionPayload(error);
    if (completion) {
      return completion;
    }
    throw error;
  }
}

export async function requestPasswordReset(email) {
  const { data } = await allauthAppRequest("post", "/auth/password/request", {
    data: { email: String(email || "").trim() },
  });
  return data;
}

export async function inspectPasswordResetKey(key) {
  const { data } = await allauthAppRequest("get", "/auth/password/reset", {
    headers: { "X-Password-Reset-Key": key },
  });
  return data;
}

export async function resetPasswordByKey({ key, password }) {
  try {
    const { data } = await allauthAppRequest("post", "/auth/password/reset", {
      data: {
        key,
        password,
      },
      headers: { "X-Password-Reset-Key": key },
    });
    return data;
  } catch (error) {
    const completion = getAnonymousCompletionPayload(error);
    if (completion) {
      return completion;
    }
    throw error;
  }
}

export async function getOAuthProviders() {
  const { data } = await sessionGet("/oauth/providers");
  return data?.providers || [];
}

export async function getOAuthLink(
  provider,
  next = "/account/security#linked",
) {
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
  const response = await allauthAppRequest("get", "/account/email");
  return normalizeEmailStatus(response?.data?.data);
}

export async function changeEmail(new_email) {
  const response = await allauthAppRequest("post", "/account/email", {
    data: { email: String(new_email || "").trim() },
  });
  return {
    ok: true,
    message: "Проверьте почту, чтобы подтвердить новый адрес.",
    ...normalizeEmailStatus(response?.data?.data),
  };
}

export async function resendEmailVerification(target_email = null) {
  const target =
    String(target_email || "").trim() ||
    (await getEmailStatus()).resend_target ||
    "";
  if (!target) {
    return {
      ok: true,
      message: "Нет адреса, который требует повторного подтверждения.",
    };
  }

  const response = await allauthAppRequest("put", "/account/email", {
    data: { email: target },
  });
  return {
    ok: response.status === 200,
    message: "Письмо для подтверждения отправлено.",
  };
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
