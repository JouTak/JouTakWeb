import { allauthAppRequest } from "../auth/sessionClient";

const EMPTY_TOTP = {
  enabled: false,
  authenticator: null,
  recovery_codes_generated: false,
  blocked_by_email_verification: false,
  secret: "",
  totp_url: "",
};

// ─── MFA Configuration ──────────────────────────────────────────────────────

/**
 * Fetch global MFA configuration (passkey login support, supported types).
 * Reads the headless config endpoint so the authenticated account pages
 * do not need to hit an MFA challenge route just to learn feature flags.
 */
export async function getMfaConfig() {
  try {
    const { data } = await allauthAppRequest("get", "/config");
    const config = data?.data?.mfa || data?.data || {};
    return {
      passkey_login_enabled: config?.passkey_login_enabled ?? false,
      supported_types: config?.supported_types || config?.types || [],
    };
  } catch (error) {
    if (error?.response?.status !== 401) {
      throw error;
    }
    const flows =
      error?.response?.data?.data?.flows || error?.response?.data?.flows || [];
    return {
      passkey_login_enabled: flows.some(
        (flow) => flow?.id === "mfa_login_webauthn",
      ),
      supported_types: [],
    };
  }
}

// ─── MFA Authentication (login / reauthentication) ──────────────────────────

/**
 * Submit a TOTP or recovery code for MFA challenge during login.
 */
export async function authenticateMfaCode(code) {
  const { data } = await allauthAppRequest("post", "/auth/2fa/authenticate", {
    data: { code: String(code || "").trim() },
  });
  return data;
}

/**
 * Get WebAuthn authentication (assertion) options for a given usage.
 * @param {"login"|"authenticate"|"reauthenticate"} usage
 */
export async function getWebAuthnRequestOptions(usage) {
  const endpoint =
    usage === "login"
      ? "/auth/webauthn/login"
      : usage === "reauthenticate"
        ? "/auth/webauthn/reauthenticate"
        : "/auth/webauthn/authenticate";
  const { data } = await allauthAppRequest("get", endpoint);
  return data?.data?.request_options || data?.data || data;
}

/**
 * Submit a signed WebAuthn credential for authentication.
 * @param {"login"|"authenticate"|"reauthenticate"} usage
 * @param {object} credential - The signed WebAuthn PublicKeyCredential
 */
export async function authenticateWithWebAuthnCredential(usage, credential) {
  const endpoint =
    usage === "login"
      ? "/auth/webauthn/login"
      : usage === "reauthenticate"
        ? "/auth/webauthn/reauthenticate"
        : "/auth/webauthn/authenticate";
  const { data } = await allauthAppRequest("post", endpoint, {
    data: { credential },
  });
  return data;
}

// ─── TOTP Management ────────────────────────────────────────────────────────

/**
 * Get current TOTP authenticator status (provisioning URI if not active).
 */
export async function getTotpStatus() {
  try {
    const { data } = await allauthAppRequest(
      "get",
      "/account/authenticators/totp",
    );
    return data?.data || data;
  } catch (error) {
    if (error?.response?.status !== 404) {
      throw error;
    }
    const meta = error?.response?.data?.meta || error?.response?.data?.data;
    if (!meta?.secret && !meta?.totp_url) {
      return EMPTY_TOTP;
    }
    return {
      ...EMPTY_TOTP,
      secret: meta.secret || "",
      totp_url: meta.totp_url || "",
    };
  }
}

/**
 * Activate (confirm) TOTP authenticator with a verification code.
 */
export async function activateTotp(code) {
  const { data } = await allauthAppRequest(
    "post",
    "/account/authenticators/totp",
    {
      data: { code: String(code || "").trim() },
    },
  );
  return data?.data || data;
}

/**
 * Deactivate TOTP authenticator.
 */
export async function deactivateTotp() {
  const { data } = await allauthAppRequest(
    "delete",
    "/account/authenticators/totp",
  );
  return data;
}

// ─── WebAuthn Credential Management ────────────────────────────────────────

/**
 * List all enrolled authenticators (TOTP, WebAuthn, recovery codes).
 */
export async function listAuthenticators() {
  const { data } = await allauthAppRequest("get", "/account/authenticators");
  return data?.data || data;
}

/**
 * Get WebAuthn registration (creation) options for adding a new credential.
 * @param {{ name?: string, passwordless?: boolean }} options
 */
export async function getWebAuthnRegistrationOptions({
  name,
  passwordless = false,
} = {}) {
  const params = {};
  if (name) params.name = name;
  if (passwordless) params.passwordless = "";
  const { data } = await allauthAppRequest(
    "get",
    "/account/authenticators/webauthn",
    { params: Object.keys(params).length ? params : undefined },
  );
  return data?.data?.creation_options || data?.data || data;
}

/**
 * Submit a newly created WebAuthn credential to register it.
 * @param {{ name?: string, credential: object }} options
 */
export async function addWebAuthnCredential({ name, credential }) {
  const { data } = await allauthAppRequest(
    "post",
    "/account/authenticators/webauthn",
    { data: { name, credential } },
  );
  return data?.data || data;
}

/**
 * Rename a WebAuthn credential.
 * @param {string|number} id - Credential ID
 * @param {string} name - New display name
 */
export async function renameWebAuthnCredential(id, name) {
  const { data } = await allauthAppRequest(
    "put",
    `/account/authenticators/webauthn/${encodeURIComponent(id)}`,
    { data: { name } },
  );
  return data;
}

/**
 * Delete one or more WebAuthn credentials.
 * @param {Array<string|number>} ids - Credential IDs to delete
 */
export async function deleteWebAuthnCredentials(ids) {
  const { data } = await allauthAppRequest(
    "delete",
    "/account/authenticators/webauthn",
    { data: { authenticators: ids } },
  );
  return data;
}

// ─── Recovery Codes ─────────────────────────────────────────────────────────

/**
 * Get current recovery codes.
 */
export async function getRecoveryCodes() {
  const { data } = await allauthAppRequest(
    "get",
    "/account/authenticators/recovery-codes",
  );
  return data?.data || data;
}

/**
 * Regenerate recovery codes (invalidates previous set).
 */
export async function regenerateRecoveryCodes() {
  const { data } = await allauthAppRequest(
    "post",
    "/account/authenticators/recovery-codes",
  );
  return data?.data || data;
}

// ─── Re-authentication ──────────────────────────────────────────────────────

/**
 * Re-authenticate with password (for sensitive operations).
 */
export async function reauthenticateWithPassword(password) {
  const { data } = await allauthAppRequest("post", "/auth/reauthenticate", {
    data: { password },
  });
  return data;
}

/**
 * Re-authenticate with a TOTP/recovery code (for sensitive operations).
 */
export async function reauthenticateWithMfaCode(code) {
  const { data } = await allauthAppRequest("post", "/auth/2fa/reauthenticate", {
    data: { code: String(code || "").trim() },
  });
  return data;
}
