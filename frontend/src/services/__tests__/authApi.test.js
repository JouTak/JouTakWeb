import { beforeEach, describe, expect, it, vi } from "vitest";

import { doLogin } from "../api/authApi";
import { tokenStore } from "../auth/tokenStore";
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
    expect(refreshSpy).not.toHaveBeenCalled();
  });
});
