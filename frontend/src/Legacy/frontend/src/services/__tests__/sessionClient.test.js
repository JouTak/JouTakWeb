import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  allauthAppRequest,
  HARD_LOGOUT_REASONS,
  requestWithSession,
  setupAxiosInterceptors,
} from "../auth/sessionClient";
import { tokenStore } from "../auth/tokenStore";
import { bareClient } from "../http/client";

function response(data = {}, headers = {}) {
  return { data, headers };
}

function httpError(status, data = {}, headers = {}) {
  const error = new Error(`HTTP ${status}`);
  error.response = { status, data, headers };
  return error;
}

describe("sessionClient", () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    setupAxiosInterceptors();
  });

  it("retries once with a rotated session token from a 401 response", async () => {
    tokenStore.set({ session_token: "old-session" });
    const request = vi
      .spyOn(bareClient, "request")
      .mockRejectedValueOnce(
        httpError(401, { meta: { session_token: "new-session" } }),
      )
      .mockResolvedValueOnce(response({ ok: true }));

    await expect(requestWithSession("get", "/account/status")).resolves.toEqual(
      response({ ok: true }),
    );

    expect(request).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-Session-Token": "new-session",
        }),
      }),
    );
    expect(tokenStore.get().session_token).toBe("new-session");
  });

  it("refreshes access token after an unauthorized request", async () => {
    tokenStore.set({ session_token: "session", access: "old-access" });
    vi.spyOn(bareClient, "post").mockResolvedValueOnce({
      data: { access: "new-access" },
    });
    const request = vi
      .spyOn(bareClient, "request")
      .mockRejectedValueOnce(httpError(401))
      .mockResolvedValueOnce(response({ ok: true }));

    await requestWithSession("get", "/auth/me", {
      rotateSessionTokenOn401: false,
    });

    expect(bareClient.post).toHaveBeenCalledWith(
      "/auth/refresh",
      {},
      expect.objectContaining({
        headers: expect.objectContaining({ "X-Session-Token": "session" }),
      }),
    );
    expect(request).toHaveBeenLastCalledWith(
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer new-access",
        }),
      }),
    );
  });

  it("hard logs out when refresh fails", async () => {
    tokenStore.set({ session_token: "session", access: "old-access" });
    const hardLogout = vi.fn();
    setupAxiosInterceptors(hardLogout);
    vi.spyOn(bareClient, "post").mockRejectedValueOnce(httpError(401));
    vi.spyOn(bareClient, "request").mockRejectedValueOnce(httpError(401));

    await expect(
      requestWithSession("get", "/auth/me", {
        rotateSessionTokenOn401: false,
      }),
    ).rejects.toThrow("HTTP 401");

    expect(tokenStore.get()).toEqual({});
    expect(hardLogout).toHaveBeenCalledWith({
      reason: HARD_LOGOUT_REASONS.REFRESH_FAILED,
    });
  });

  it("can call allauth app endpoints without stored auth headers", async () => {
    tokenStore.set({ session_token: "session", access: "access-token" });
    const request = vi
      .spyOn(bareClient, "request")
      .mockResolvedValueOnce(response({ ok: true }));

    await allauthAppRequest("get", "/auth/email/verify", {
      headers: { "X-Email-Verification-Key": "key" },
      includeSession: false,
    });

    expect(request).toHaveBeenCalledWith(
      expect.objectContaining({
        headers: expect.not.objectContaining({
          Authorization: "Bearer access-token",
          "X-Session-Token": "session",
        }),
      }),
    );
    expect(request).toHaveBeenCalledWith(
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-Allauth-Client": "app",
          "X-Client": "app",
          "X-Email-Verification-Key": "key",
        }),
      }),
    );
  });
});
