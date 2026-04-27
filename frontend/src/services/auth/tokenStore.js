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
    legacyTokenStorage()?.removeItem(TOKENS_KEY);
    return {};
  }

  const tokens = readJsonTokens(storage.getItem(TOKENS_KEY));
  if (Object.keys(tokens).length > 0) {
    return tokens;
  }

  const legacyStorage = legacyTokenStorage();
  const legacyTokens = readJsonTokens(legacyStorage?.getItem(TOKENS_KEY));
  const { refresh, ...migratedTokens } = legacyTokens;
  void refresh;
  if (Object.keys(migratedTokens).length > 0) {
    storage.setItem(TOKENS_KEY, JSON.stringify(migratedTokens));
    legacyStorage?.removeItem(TOKENS_KEY);
  }
  return migratedTokens;
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
  legacyTokenStorage()?.removeItem(TOKENS_KEY);

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
