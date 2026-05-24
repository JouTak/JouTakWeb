import { beforeEach, describe, expect, it, vi } from "vitest";

import { authenticateMfaCode, getTotpStatus } from "../api/mfaApi";
import { tokenStore } from "../auth/tokenStore";
import { bareClient } from "../http/client";

function httpError(status, data = {}, headers = {}) {
  const error = new Error(`HTTP ${status}`);
  error.response = { status, data, headers };
  return error;
}

describe("mfaApi", () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("normalizes missing TOTP setup into a setup payload", async () => {
    vi.spyOn(bareClient, "request").mockRejectedValueOnce(
      httpError(404, {
        meta: {
          secret: "otpauth-secret",
          totp_url: "otpauth://totp/example",
        },
      }),
    );

    await expect(getTotpStatus()).resolves.toEqual({
      enabled: false,
      authenticator: null,
      recovery_codes_generated: false,
      blocked_by_email_verification: false,
      secret: "otpauth-secret",
      totp_url: "otpauth://totp/example",
    });
  });

  it("stores session token when MFA authenticate returns a pending session", async () => {
    vi.spyOn(bareClient, "request").mockRejectedValueOnce(
      httpError(401, {
        data: {
          status: 401,
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

    await expect(authenticateMfaCode("123456")).rejects.toMatchObject({
      response: expect.objectContaining({ status: 401 }),
    });

    expect(tokenStore.get().session_token).toBe("mfa-session-token");
  });
});
