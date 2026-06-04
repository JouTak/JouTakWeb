import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  AUTH_STATE_EVENT,
  clearAuthState,
  hasStoredAuth,
  markPendingMfaSession,
  migrateLegacyTokenStorage,
  TOKENS_KEY,
  tokenStore,
} from "../auth/tokenStore";

describe("tokenStore", () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
  });

  it("stores tokens in sessionStorage and emits auth state changes", () => {
    const listener = vi.fn();
    window.addEventListener(AUTH_STATE_EVENT, listener);

    tokenStore.set({ session_token: "session-1", access: "access-1" });

    expect(JSON.parse(sessionStorage.getItem(TOKENS_KEY))).toEqual({
      session_token: "session-1",
      access: "access-1",
    });
    expect(hasStoredAuth()).toBe(true);
    expect(listener).toHaveBeenCalledTimes(1);

    tokenStore.set({ session_token: "session-2" });
    expect(listener).toHaveBeenCalledTimes(1);

    clearAuthState();
    expect(sessionStorage.getItem(TOKENS_KEY)).toBeNull();
    expect(hasStoredAuth()).toBe(false);
    expect(listener).toHaveBeenCalledTimes(2);
  });

  it("migrates legacy localStorage tokens without refresh", () => {
    localStorage.setItem(
      TOKENS_KEY,
      JSON.stringify({
        session_token: "legacy-session",
        access: "legacy-access",
        refresh: "legacy-refresh",
      }),
    );

    migrateLegacyTokenStorage();

    expect(tokenStore.get()).toEqual({
      session_token: "legacy-session",
      access: "legacy-access",
    });
    expect(localStorage.getItem(TOKENS_KEY)).toBeNull();
    expect(JSON.parse(sessionStorage.getItem(TOKENS_KEY))).toEqual({
      session_token: "legacy-session",
      access: "legacy-access",
    });
  });

  it("does not overwrite existing sessionStorage tokens on migration", () => {
    sessionStorage.setItem(
      TOKENS_KEY,
      JSON.stringify({ session_token: "current" }),
    );
    localStorage.setItem(
      TOKENS_KEY,
      JSON.stringify({ session_token: "legacy" }),
    );

    migrateLegacyTokenStorage();

    expect(tokenStore.get()).toEqual({ session_token: "current" });
    expect(localStorage.getItem(TOKENS_KEY)).toBeNull();
  });

  it("ignores malformed token JSON", () => {
    sessionStorage.setItem(TOKENS_KEY, "{bad json");

    expect(tokenStore.get()).toEqual({});
    expect(hasStoredAuth()).toBe(false);
  });

  it("marks and clears pending mfa without dropping the session token", () => {
    tokenStore.set({ session_token: "session-1", access: "access-1" });
    const listener = vi.fn();
    window.addEventListener(AUTH_STATE_EVENT, listener);

    markPendingMfaSession(true);
    expect(tokenStore.get()).toEqual({
      session_token: "session-1",
      access: "access-1",
      pending_mfa: true,
    });
    expect(listener).toHaveBeenCalledTimes(1);

    markPendingMfaSession(false);
    expect(tokenStore.get()).toEqual({
      session_token: "session-1",
      access: "access-1",
    });
    expect(listener).toHaveBeenCalledTimes(2);
  });
});
