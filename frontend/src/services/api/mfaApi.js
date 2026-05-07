import { allauthAppRequest } from "../auth/sessionClient";

// ─── MFA Configuration ──────────────────────────────────────────────────────

/**
 * Fetch global MFA configuration (passkey login support, supported types).
 * Falls back to allauth headless config endpoint.
 */
export async function getMfaConfig() {
  const { data } = await allauthAppRequest("get", "/auth/2fa/authenticate", {
    includeSession: false,
  });
  const config = data?.data || {};
  return {
    passkey_login_enabled: config?.passkey_login_enabled ?? false,
    supported_types: config?.types || [],
  };
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
    usage === "login" ? "/auth/webauthn/login" : "/auth/webauthn/authenticate";
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
    usage === "login" ? "/auth/webauthn/login" : "/auth/webauthn/authenticate";
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
  const { data } = await allauthAppRequest(
    "get",
    "/account/authenticators/totp",
  );
  return data?.data || data;
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
 * @param {{ name?: string }} options
 */
export async function getWebAuthnRegistrationOptions({ name } = {}) {
  const { data } = await allauthAppRequest(
    "get",
    "/account/authenticators/webauthn",
    { params: name ? { name } : undefined },
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
  const { data } = await allauthAppRequest("post", "/auth/reauthenticate", {
    data: { code: String(code || "").trim() },
  });
  return data;
}
