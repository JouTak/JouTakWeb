import axios from "axios";

export const BACKEND_URL = "__REACT_APP_API_URL__";
const API_BASE = `${BACKEND_URL.replace(/\/$/, "")}/api`;
const TOKENS_KEY = "joutak_auth";

export function setupAxiosInterceptors(onHardLogout = () => {}) {
  const saved = tokenStore.get();
  if (saved?.access) setAuthHeader(saved.access);

  axios.interceptors.response.use(
    (r) => r,
    async (error) => {
      const { response, config } = error || {};
      if (!response) return Promise.reject(error);
      if (config?.__noGlobal401) return Promise.reject(error);

      const is401 = response.status === 401;
      const isRefreshCall = config?.url?.includes("/api/auth/refresh");
      const isSessionExchange = config?.url?.includes(
        "/api/auth/jwt/from_session",
      );

      if (!is401 || isRefreshCall || isSessionExchange) {
        return Promise.reject(error);
      }

      const tokens = tokenStore.get();
      const refresh = tokens?.refresh;
      if (!refresh) {
        onHardLogout();
        return Promise.reject(error);
      }

      try {
        config.__retry = true;
        const { data } = await axios.post(`${API_BASE}/auth/refresh`, {
          refresh,
        });
        const newAccess = data?.access;
        const newRefresh = data?.refresh || refresh;
        tokenStore.set({ ...tokens, access: newAccess, refresh: newRefresh });
        setAuthHeader(newAccess);
        return axios(config);
      } catch (e) {
        onHardLogout();
        tokenStore.clear();
        setAuthHeader();
        return Promise.reject(e);
      }
    },
  );
}

export const tokenStore = {
  get() {
    try {
      return JSON.parse(localStorage.getItem(TOKENS_KEY) || "{}");
    } catch {
      return {};
    }
  },
  set(tokens) {
    localStorage.setItem(TOKENS_KEY, JSON.stringify(tokens || {}));
  },
  clear() {
    localStorage.removeItem(TOKENS_KEY);
  },
  getSessionToken() {
    return tokenStore.get()?.session_token || null;
  },
};

export const setAuthHeader = (access) => {
  if (access) axios.defaults.headers.common.Authorization = `Bearer ${access}`;
  else delete axios.defaults.headers.common.Authorization;
};

const takeSessionToken = (respOrErrResp) => {
  const meta = respOrErrResp?.data?.meta || {};
  return (
    meta.session_token || respOrErrResp?.headers?.["x-session-token"] || null
  );
};

const withSessionHeaders = (sessionToken) => ({
  headers: {
    ...(sessionToken ? { "X-Session-Token": sessionToken } : {}),
    "X-Client": "app",
    "X-Allauth-Client": "app",
  },
});

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

async function postWithSession(url, body) {
  const st = tokenStore.getSessionToken();
  try {
    const resp = await axios.post(url, body, {
      ...withSessionHeaders(st),
      __noGlobal401: true,
    });
    const st2 = takeSessionToken(resp);
    if (st2 && st2 !== st)
      tokenStore.set({ ...tokenStore.get(), session_token: st2 });
    return resp;
  } catch (e) {
    const r = e?.response;
    const st3 = takeSessionToken(r);
    if (r?.status === 401 && st3) {
      tokenStore.set({ ...tokenStore.get(), session_token: st3 });
      return await axios.post(url, body, {
        ...withSessionHeaders(st3),
        __noGlobal401: true,
      });
    }
    throw e;
  }
}

async function getWithSession(url, params) {
  const st = tokenStore.getSessionToken();
  try {
    const resp = await axios.get(url, {
      ...withSessionHeaders(st),
      params,
      __noGlobal401: true,
    });
    const st2 = takeSessionToken(resp);
    if (st2 && st2 !== st)
      tokenStore.set({ ...tokenStore.get(), session_token: st2 });
    return resp;
  } catch (e) {
    const r = e?.response;
    const st3 = takeSessionToken(r);
    if (r?.status === 401 && st3) {
      tokenStore.set({ ...tokenStore.get(), session_token: st3 });
      return await axios.get(url, {
        ...withSessionHeaders(st3),
        params,
        __noGlobal401: true,
      });
    }
    throw e;
  }
}

async function delWithSession(url, params) {
  const st = tokenStore.getSessionToken();
  try {
    const resp = await axios.delete(url, {
      ...withSessionHeaders(st),
      params,
      __noGlobal401: true,
    });
    const st2 = takeSessionToken(resp);
    if (st2 && st2 !== st)
      tokenStore.set({ ...tokenStore.get(), session_token: st2 });
    return resp;
  } catch (e) {
    const r = e?.response;
    const st3 = takeSessionToken(r);
    if (r?.status === 401 && st3) {
      tokenStore.set({ ...tokenStore.get(), session_token: st3 });
      return await axios.delete(url, {
        ...withSessionHeaders(st3),
        params,
        __noGlobal401: true,
      });
    }
    throw e;
  }
}

export async function loginApp({ username, password }) {
  const { data, headers } = await axios.post(`${API_BASE}/auth/login`, {
    username: String(username || "").trim(),
    password,
  });
  const st = takeSessionToken({ data, headers });
  if (!st) throw new Error("No session token returned on login");
  tokenStore.set({ ...tokenStore.get(), session_token: st });
  return st;
}

export async function signupApp({ username, email, password }) {
  const body = {
    username: String(username || "").trim(),
    email: String(email || "").trim(),
    password: password,
  };
  const { data, headers } = await axios.post(`${API_BASE}/auth/signup`, body);
  const st = takeSessionToken({ data, headers });
  if (!st) throw new Error("No session token returned on signup");
  tokenStore.set({ ...tokenStore.get(), session_token: st });
  return st;
}

export async function jwtFromSession() {
  const resp = await postWithSession(`${API_BASE}/auth/jwt/from_session`, null);
  const pair = resp.data;
  tokenStore.set({ ...tokenStore.get(), ...pair });
  setAuthHeader(pair.access);
  return pair;
}

export async function doLogin({ username, password }) {
  await loginApp({ username, password });
  try {
    await jwtFromSession();
  } catch {}
  return tokenStore.get();
}

export async function doSignupAndLogin({ username, email, password }) {
  await signupApp({ username, email, password });
  try {
    await jwtFromSession();
  } catch {}
  return tokenStore.get();
}

export async function logout() {
  try {
    await postWithSession(`${API_BASE}/auth/logout`, null);
  } finally {
    tokenStore.clear();
    setAuthHeader();
  }
}

export async function me() {
  const { data } = await getWithSession(`${API_BASE}/auth/me`);
  return data;
}

export async function changePassword({ current_password, new_password }) {
  const { data } = await postWithSession(`${API_BASE}/auth/change_password`, {
    current_password,
    new_password,
  });
  return data;
}

export async function getOAuthProviders() {
  const { data } = await getWithSession(`${API_BASE}/oauth/providers`);
  return data?.providers || [];
}

export async function getOAuthLink(
  provider,
  next = "/account/security#linked",
) {
  const { data } = await getWithSession(`${API_BASE}/oauth/link/${provider}`, {
    next,
  });
  return {
    url: sanitizeUrl(data.authorize_url),
    method: data.method || "POST",
  };
}

export async function listSessionsHeadless() {
  const { data } = await getWithSession(`${API_BASE}/account/sessions`);
  return data;
}

export async function revokeSessionHeadless(session_id, reason = "manual") {
  const resp = await delWithSession(
    `${API_BASE}/account/sessions/${encodeURIComponent(session_id)}`,
    { reason },
  );
  return resp.data;
}

export async function bulkRevokeSessionsHeadless() {
  const { data } = await postWithSession(`${API_BASE}/account/sessions/_bulk`, {
    all_except_current: true,
    reason: "bulk_except_current",
  });
  return data;
}

export async function getEmailStatus() {
  const { data } = await getWithSession(`${API_BASE}/account/email`);
  return data;
}

export async function changeEmail(new_email) {
  const { data } = await postWithSession(`${API_BASE}/account/email/change`, {
    new_email,
  });
  return data;
}

export async function resendEmailVerification() {
  const { data } = await postWithSession(
    `${API_BASE}/account/email/resend`,
    null,
  );
  return data;
}

async function patchWithSession(url, body) {
  const st = tokenStore.getSessionToken();
  try {
    const resp = await axios.patch(url, body, {
      ...withSessionHeaders(st),
      __noGlobal401: true,
    });
    const st2 = takeSessionToken(resp);
    if (st2 && st2 !== st)
      tokenStore.set({ ...tokenStore.get(), session_token: st2 });
    return resp;
  } catch (e) {
    const r = e?.response;
    const st3 = takeSessionToken(r);
    if (r?.status === 401 && st3) {
      tokenStore.set({ ...tokenStore.get(), session_token: st3 });
      return await axios.patch(url, body, {
        ...withSessionHeaders(st3),
        __noGlobal401: true,
      });
    }
    throw e;
  }
}

export async function updateProfile({ first_name = null, last_name = null }) {
  const { data } = await patchWithSession(`${API_BASE}/account/profile`, {
    ...(first_name !== undefined ? { first_name } : {}),
    ...(last_name !== undefined ? { last_name } : {}),
  });
  return data;
}
