import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  authenticateMfaCode,
  authenticateWithWebAuthnCredential,
  getMfaConfig,
  getTotpStatus,
  getWebAuthnRegistrationOptions,
  getWebAuthnRequestOptions,
  reauthenticateWithMfaCode,
} from "../api/mfaApi";
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

  it("routes MFA reauthentication codes to the MFA reauth endpoint", async () => {
    const requestSpy = vi.spyOn(bareClient, "request").mockResolvedValueOnce({
      data: {
        data: {
          status: "ok",
        },
      },
    });

    await expect(reauthenticateWithMfaCode(" 123456 ")).resolves.toEqual({
      data: {
        status: "ok",
      },
    });

    expect(requestSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        method: "post",
        url: "auth/flow/app/v1/auth/2fa/reauthenticate",
        data: { code: "123456" },
      }),
    );
  });

  it("reads MFA config from the headless config endpoint", async () => {
    const requestSpy = vi.spyOn(bareClient, "request").mockResolvedValueOnce({
      data: {
        data: {
          mfa: {
            supported_types: ["totp", "webauthn"],
            passkey_login_enabled: true,
          },
        },
      },
    });

    await expect(getMfaConfig()).resolves.toEqual({
      supported_types: ["totp", "webauthn"],
      passkey_login_enabled: true,
    });

    expect(requestSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        method: "get",
        url: "auth/flow/app/v1/config",
      }),
    );
  });

  it("derives passkey login support from unauthenticated config flows", async () => {
    vi.spyOn(bareClient, "request").mockRejectedValueOnce(
      httpError(401, {
        data: {
          flows: [
            { id: "login" },
            { id: "signup" },
            { id: "mfa_login_webauthn" },
          ],
        },
        meta: {
          is_authenticated: null,
        },
      }),
    );

    await expect(getMfaConfig()).resolves.toEqual({
      supported_types: [],
      passkey_login_enabled: true,
    });
  });

  it("requests reauthentication WebAuthn options from the dedicated endpoint", async () => {
    const requestSpy = vi.spyOn(bareClient, "request").mockResolvedValueOnce({
      data: {
        data: {
          request_options: {
            challenge: "abc",
            rpId: "joutak.ru",
            rp: { id: "joutak.ru", name: "JouTak" },
          },
        },
      },
    });

    await expect(getWebAuthnRequestOptions("reauthenticate")).resolves.toEqual({
      challenge: "abc",
      rpId: "joutak.ru",
      rp: { id: "joutak.ru", name: "JouTak" },
    });

    expect(requestSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        method: "get",
        url: "auth/flow/app/v1/auth/webauthn/reauthenticate",
      }),
    );
  });

  it("posts reauthentication WebAuthn credentials to the dedicated endpoint", async () => {
    const requestSpy = vi.spyOn(bareClient, "request").mockResolvedValueOnce({
      data: {
        data: {
          status: "ok",
        },
      },
    });

    const credential = { type: "public-key", id: "cred" };

    await expect(
      authenticateWithWebAuthnCredential("reauthenticate", credential),
    ).resolves.toEqual({
      data: {
        status: "ok",
      },
    });

    expect(requestSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        method: "post",
        url: "auth/flow/app/v1/auth/webauthn/reauthenticate",
        data: { credential },
      }),
    );
  });

  it("forwards passwordless registration mode when requested", async () => {
    const requestSpy = vi.spyOn(bareClient, "request").mockResolvedValueOnce({
      data: {
        data: {
          creation_options: {
            challenge: "abc",
            rp: { id: "joutak.ru", name: "JouTak" },
          },
        },
      },
    });

    await expect(
      getWebAuthnRegistrationOptions({ passwordless: true }),
    ).resolves.toEqual({
      challenge: "abc",
      rp: { id: "joutak.ru", name: "JouTak" },
    });

    expect(requestSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        method: "get",
        url: "auth/flow/app/v1/account/authenticators/webauthn",
        params: { passwordless: "" },
      }),
    );
  });
});
