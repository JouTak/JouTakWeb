import {
  allauthAppRequest,
  sessionGet,
  sessionPost,
} from "../auth/sessionClient";
import {
  clearAuthStorage,
  mergeStoredTokens,
  tokenStore,
} from "../auth/tokenStore";

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

export async function loginApp({ login, password }) {
  const response = await allauthAppRequest("post", "/auth/login", {
    data: {
      username: String(login || "").trim(),
      password,
    },
  });

  const sessionToken =
    response?.data?.meta?.session_token ||
    response?.headers?.["x-session-token"] ||
    null;
  if (!sessionToken) {
    throw new Error("No session token returned on login");
  }

  mergeStoredTokens({ session_token: sessionToken }, { emit: true });
  return sessionToken;
}

export async function signupApp({ email, password }) {
  const response = await allauthAppRequest("post", "/auth/signup", {
    data: {
      email: String(email || "").trim(),
      password,
    },
  });

  const sessionToken =
    response?.data?.meta?.session_token ||
    response?.headers?.["x-session-token"] ||
    null;
  if (!sessionToken) {
    throw new Error("No session token returned on signup");
  }

  mergeStoredTokens({ session_token: sessionToken }, { emit: true });
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
      refresh: null,
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
