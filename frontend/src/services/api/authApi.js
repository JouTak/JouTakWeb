import {
  allauthAppRequest,
  extractSessionToken,
  sessionGet,
  sessionPost,
} from "../auth/sessionClient";
import {
  clearAuthStorage,
  markPendingMfaSession,
  mergeStoredTokens,
  tokenStore,
} from "../auth/tokenStore";

function extractPendingMfa(payload) {
  const flows = Array.isArray(payload?.data?.flows) ? payload.data.flows : [];
  const pending = flows.find((flow) => flow?.id === "mfa_authenticate") || null;
  if (!pending) {
    return null;
  }
  return {
    status: "pending_mfa",
    flows,
    types: Array.isArray(pending?.types) ? pending.types : [],
    session_token: payload?.meta?.session_token || null,
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

export async function loginApp({ login, password }) {
  try {
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
    return {
      status: "authenticated",
      session_token: sessionToken,
    };
  } catch (error) {
    const sessionToken = extractSessionToken(error?.response);
    const pending = extractPendingMfa(error?.response?.data);
    if (pending && sessionToken) {
      mergeStoredTokens(
        { session_token: sessionToken, pending_mfa: true },
        { emit: false },
      );
      return {
        ...pending,
        session_token: sessionToken,
      };
    }
    throw error;
  }
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
  const result = await loginApp({ login, password });
  if (result?.status === "pending_mfa") {
    return result;
  }
  try {
    await jwtFromSession();
  } catch {
    // Session can still be valid for headless endpoints even if JWT exchange fails.
  }
  return {
    status: "authenticated",
    tokens: tokenStore.get(),
  };
}

export async function doSignupAndLogin({ email, password }) {
  await signupApp({ email, password });
  try {
    await jwtFromSession();
  } catch {
    // Session can still be valid for headless endpoints even if JWT exchange fails.
  }
  return {
    status: "authenticated",
    tokens: tokenStore.get(),
  };
}

export async function finalizeSessionAuthentication() {
  try {
    await jwtFromSession();
  } catch {
    // Headless session may still be usable for app endpoints.
  }
  markPendingMfaSession(false);
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
    includeSession: false,
  });
  return data;
}

export async function confirmEmailVerification(key) {
  try {
    const { data } = await allauthAppRequest("post", "/auth/email/verify", {
      data: { key },
      headers: { "X-Email-Verification-Key": key },
      includeSession: false,
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
