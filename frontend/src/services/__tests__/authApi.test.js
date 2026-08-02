import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  announceAuthenticatedSession,
  doLogin,
  finalizeSessionAuthentication,
} from "../api/authApi";
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
