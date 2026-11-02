import { sessionGet } from "../auth/sessionClient";

export async function getMemberships() {
  return (await sessionGet("/account/memberships")).data;
}
export async function getServerMemberships() {
  return (await sessionGet("/account/server-communities")).data;
}
export async function getCommunities(page = 1) {
  return (
    await sessionGet("/communities", { page }, { hardLogoutOn401: false })
  ).data;
}
export async function getCommunity(slug) {
  return (
    await sessionGet(`/communities/${encodeURIComponent(slug)}`, undefined, {
      hardLogoutOn401: false,
    })
  ).data;
}
