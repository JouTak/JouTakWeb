export const TOKENS_KEY = "joutak_auth";
export const AUTH_STATE_EVENT = "joutak:auth-state-changed";

function hasAuthTokens(tokens) {
  return Boolean(tokens?.session_token || tokens?.access);
}

function emitAuthStateChanged() {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new Event(AUTH_STATE_EVENT));
}

function browserStorage(name) {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window[name] || null;
  } catch {
    return null;
  }
}

function tokenStorage() {
  return browserStorage("sessionStorage");
}

function legacyTokenStorage() {
  return browserStorage("localStorage");
}

function readJsonTokens(raw) {
  try {
    const parsed = JSON.parse(raw || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

export function readStoredTokens() {
  const storage = tokenStorage();
  if (!storage) {
    return {};
  }
  return readJsonTokens(storage.getItem(TOKENS_KEY));
}

/**
 * One-shot migration: if tokens live in `localStorage` (legacy), move
 * them into `sessionStorage` and drop the legacy entry. Call this once
 * at application startup; subsequent reads use `readStoredTokens`
 * unconditionally and stay O(1).
 */
export function migrateLegacyTokenStorage() {
  const storage = tokenStorage();
  const legacyStorage = legacyTokenStorage();

  if (!storage) {
    legacyStorage?.removeItem(TOKENS_KEY);
    return;
  }

  if (storage.getItem(TOKENS_KEY) !== null) {
    legacyStorage?.removeItem(TOKENS_KEY);
    return;
  }

  const legacyRaw = legacyStorage?.getItem(TOKENS_KEY);
  if (!legacyRaw) {
    return;
  }

  const legacyTokens = readJsonTokens(legacyRaw);
  // Never migrate the old long-lived refresh token: it must only live
  // in the HttpOnly cookie issued by the backend.
  const { refresh: _legacyRefresh, ...migratedTokens } = legacyTokens;
  void _legacyRefresh;
  if (Object.keys(migratedTokens).length > 0) {
    storage.setItem(TOKENS_KEY, JSON.stringify(migratedTokens));
  }
  legacyStorage?.removeItem(TOKENS_KEY);
}

export function writeStoredTokens(tokens, { emit = true } = {}) {
  const previousTokens = readStoredTokens();
  const storage = tokenStorage();
  const nextTokens = tokens && typeof tokens === "object" ? tokens : {};

  if (Object.keys(nextTokens).length === 0) {
    storage?.removeItem(TOKENS_KEY);
  } else if (storage) {
    storage.setItem(TOKENS_KEY, JSON.stringify(nextTokens));
  }

  if (emit) {
    const previousState = hasAuthTokens(previousTokens);
    const nextState = hasAuthTokens(nextTokens);
    if (previousState !== nextState) {
      emitAuthStateChanged();
    }
  }
}

export function mergeStoredTokens(partial, { emit = true } = {}) {
  const currentTokens = readStoredTokens();
  const nextTokens = { ...currentTokens };
  Object.entries(partial || {}).forEach(([key, value]) => {
    if (value === null || value === undefined) {
      delete nextTokens[key];
      return;
    }
    nextTokens[key] = value;
  });
  writeStoredTokens(nextTokens, { emit });
}

export function markPendingMfaSession(pending = true) {
  const currentTokens = readStoredTokens();
  if (!pending) {
    if (!currentTokens.pending_mfa) return;
    const { pending_mfa: _pendingMfa, ...rest } = currentTokens;
    void _pendingMfa;
    writeStoredTokens(rest, { emit: false });
    emitAuthStateChanged();
    return;
  }
  if (!currentTokens.session_token) return;
  if (currentTokens.pending_mfa) return;
  writeStoredTokens({ ...currentTokens, pending_mfa: true }, { emit: false });
  emitAuthStateChanged();
}

export function clearAuthStorage({ emit = true } = {}) {
  writeStoredTokens({}, { emit });
}

export function hasStoredAuth() {
  return hasAuthTokens(readStoredTokens());
}

export function clearAuthState() {
  clearAuthStorage({ emit: true });
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
