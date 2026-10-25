import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  announceAuthenticatedSession,
  doLogin,
  doSignupAndLogin,
  finalizeSessionAuthentication,
} from "../api/authApi";
import {
  authenticateMfaCode,
  authenticateWithWebAuthnCredential,
  getWebAuthnRequestOptions,
} from "../api/mfaApi";
import { AUTH_STATE_EVENT, tokenStore } from "../auth/tokenStore";
import { bareClient } from "../http/client";

function httpError(status, data = {}, headers = {}) {
  const error = new Error(`HTTP ${status}`);
  error.response = { status, data, headers };
  return error;
}

describe("authApi MFA login", () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("returns pending_mfa and preserves the session token from allauth", async () => {
    const authStateListener = vi.fn();
    window.addEventListener(AUTH_STATE_EVENT, authStateListener);
    vi.spyOn(bareClient, "request").mockRejectedValueOnce(
      httpError(401, {
        status: 401,
        data: {
          flows: [
            { id: "mfa_authenticate", is_pending: true, types: ["totp"] },
          ],
        },
        meta: {
          is_authenticated: false,
          session_token: "mfa-session-token",
        },
      }),
    );
    const refreshSpy = vi.spyOn(bareClient, "post");

    await expect(
      doLogin({ login: "player@example.com", password: "StrongPass123!" }),
    ).resolves.toEqual({
      status: "pending_mfa",
      flows: [{ id: "mfa_authenticate", is_pending: true, types: ["totp"] }],
      session_token: "mfa-session-token",
      types: ["totp"],
    });

    expect(tokenStore.get().session_token).toBe("mfa-session-token");
    expect(tokenStore.get().pending_mfa).toBe(true);
    expect(authStateListener).toHaveBeenCalled();
    expect(refreshSpy).not.toHaveBeenCalled();
    window.removeEventListener(AUTH_STATE_EVENT, authStateListener);
  });

  it("publishes successful auth only after one JWT exchange", async () => {
    const authStateListener = vi.fn();
    window.addEventListener(AUTH_STATE_EVENT, authStateListener);
    const requestSpy = vi
      .spyOn(bareClient, "request")
      .mockResolvedValueOnce({
        data: { meta: { session_token: "authenticated-session" } },
        headers: {},
      })
      .mockResolvedValueOnce({ data: { access: "access-token" }, headers: {} });

    await expect(
      doLogin({ login: "player@example.com", password: "StrongPass123!" }),
    ).resolves.toMatchObject({ status: "authenticated" });
    expect(authStateListener).not.toHaveBeenCalled();

    await finalizeSessionAuthentication();
    expect(authStateListener).not.toHaveBeenCalled();
    expect(requestSpy).toHaveBeenCalledTimes(2);
    expect(requestSpy.mock.calls[1][0]).toMatchObject({
      method: "post",
      url: "/auth/jwt/from_session",
    });

    announceAuthenticatedSession();
    expect(authStateListener).toHaveBeenCalledTimes(1);
    window.removeEventListener(AUTH_STATE_EVENT, authStateListener);
  });
});

describe("session bootstrap failures", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("keeps MFA pending if the JWT exchange fails", async () => {
    tokenStore.set({ session_token: "mfa-session", pending_mfa: true });
    const request = vi
      .spyOn(bareClient, "request")
      .mockRejectedValue(httpError(503));
    await expect(finalizeSessionAuthentication()).rejects.toThrow("HTTP 503");
    expect(tokenStore.get().pending_mfa).toBe(true);
    expect(request).toHaveBeenCalledTimes(1);
  });

  it("rejects an exchange without an access token", async () => {
    vi.spyOn(bareClient, "request").mockResolvedValue({ data: {} });
    await expect(finalizeSessionAuthentication()).rejects.toThrow(
      "Access token is missing",
    );
  });
});

describe("signup and passkey bootstrap", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("exchanges signup once without publishing auth before the profile loads", async () => {
    const listener = vi.spyOn(window, "dispatchEvent");
    const request = vi
      .spyOn(bareClient, "request")
      .mockResolvedValueOnce({ data: { meta: { session_token: "signup" } } })
      .mockResolvedValueOnce({ data: { access: "jwt" } });
    await doSignupAndLogin({
      email: "new@example.com",
      password: "StrongPass123!",
    });
    expect(request).toHaveBeenCalledTimes(2);
    expect(tokenStore.get()).toEqual({
      session_token: "signup",
      access: "jwt",
    });
    expect(listener).not.toHaveBeenCalled();
  });

  it("propagates signup exchange failures", async () => {
    vi.spyOn(bareClient, "request")
      .mockResolvedValueOnce({ data: { meta: { session_token: "signup" } } })
      .mockRejectedValueOnce(httpError(503));
    await expect(
      doSignupAndLogin({
        email: "new@example.com",
        password: "StrongPass123!",
      }),
    ).rejects.toThrow("HTTP 503");
  });

  it("does not announce the anonymous session returned by passkey options", async () => {
    const listener = vi.spyOn(window, "dispatchEvent");
    vi.spyOn(bareClient, "request").mockResolvedValue({
      data: {
        meta: { session_token: "anonymous-passkey" },
        data: { request_options: {} },
      },
    });
    await getWebAuthnRequestOptions("login");
    expect(tokenStore.get().session_token).toBe("anonymous-passkey");
    expect(listener).not.toHaveBeenCalled();
  });

  it.each(["code", "passkey"])(
    "does not announce %s challenge completion before JWT bootstrap",
    async (method) => {
      tokenStore.set({ session_token: "pending", pending_mfa: true });
      const listener = vi.spyOn(window, "dispatchEvent");
      vi.spyOn(bareClient, "request").mockResolvedValue({
        data: { meta: { session_token: "completed" } },
      });
      if (method === "code") await authenticateMfaCode("123456");
      else await authenticateWithWebAuthnCredential("authenticate", {});
      expect(tokenStore.get().session_token).toBe("completed");
      expect(tokenStore.get().pending_mfa).toBe(true);
      expect(listener).not.toHaveBeenCalled();
    },
  );
});
