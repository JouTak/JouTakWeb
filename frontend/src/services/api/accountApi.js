import {
  allauthAppRequest,
  sessionDelete,
  sessionGet,
  sessionPatch,
  sessionPost,
} from "../auth/sessionClient";
import { sanitizeUrl } from "../urlSafety";

function normalizeEmailStatus(addresses) {
  const items = Array.isArray(addresses) ? addresses : [];
  const primary = items.find((item) => item?.primary) || items[0] || null;
  const pending =
    items.find((item) => item && !item.primary && !item.verified) || null;
  const resendTarget =
    pending?.email ||
    (primary && !primary.verified ? primary.email : null) ||
    null;

  return {
    email: primary?.email || "",
    verified: !!primary?.verified,
    pending_email: pending?.email || null,
    resend_target: resendTarget,
    addresses: items,
  };
}

export async function getOAuthProviders() {
  const { data } = await sessionGet("/oauth/providers");
  return data?.providers || [];
}

export async function getOAuthLink(
  provider,
  next = "/account/security#linked",
) {
  const { data } = await sessionGet(`/oauth/link/${provider}`, { next });
  return {
    url: sanitizeUrl(data?.authorize_url),
    method: data?.method || "POST",
  };
}

export async function listSessionsHeadless() {
  const { data } = await sessionGet("/account/sessions");
  return data;
}

export async function revokeSessionHeadless(session_id, reason = "manual") {
  const response = await sessionDelete(
    `/account/sessions/${encodeURIComponent(session_id)}`,
    { reason },
  );
  return response.data;
}

export async function bulkRevokeSessionsHeadless() {
  const { data } = await sessionPost("/account/sessions/bulk", {
    all_except_current: true,
    reason: "bulk_except_current",
  });
  return data;
}

export async function getEmailStatus() {
  const response = await allauthAppRequest("get", "/account/email");
  return normalizeEmailStatus(response?.data?.data);
}

export async function changeEmail(new_email) {
  const response = await allauthAppRequest("post", "/account/email", {
    data: { email: String(new_email || "").trim() },
  });
  return {
    ok: true,
    message: "Проверьте почту, чтобы подтвердить новый адрес.",
    ...normalizeEmailStatus(response?.data?.data),
  };
}

export async function resendEmailVerification(target_email = null) {
  const target =
    String(target_email || "").trim() ||
    (await getEmailStatus()).resend_target ||
    "";
  if (!target) {
    return {
      ok: true,
      message: "Нет адреса, который требует повторного подтверждения.",
    };
  }

  const response = await allauthAppRequest("put", "/account/email", {
    data: { email: target },
  });
  return {
    ok: response.status === 200,
    message: "Письмо для подтверждения отправлено.",
  };
}

export async function getAccountStatus() {
  const { data } = await sessionGet("/account/status");
  return data;
}

export async function deleteCurrentAccount(current_password) {
  const { data } = await sessionPost("/account/delete", { current_password });
  return data;
}

export async function updateProfile(payload = {}) {
  const {
    first_name,
    last_name,
    vk_username,
    minecraft_nick,
    minecraft_has_license,
    is_itmo_student,
    itmo_isu,
  } = payload;

  const { data } = await sessionPatch("/account/profile", {
    ...(first_name !== undefined ? { first_name } : {}),
    ...(last_name !== undefined ? { last_name } : {}),
    ...(vk_username !== undefined ? { vk_username } : {}),
    ...(minecraft_nick !== undefined ? { minecraft_nick } : {}),
    ...(minecraft_has_license !== undefined ? { minecraft_has_license } : {}),
    ...(is_itmo_student !== undefined ? { is_itmo_student } : {}),
    ...(itmo_isu !== undefined ? { itmo_isu } : {}),
  });

  return data;
}
