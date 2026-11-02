import { sessionDelete, sessionGet, sessionPost } from "../auth/sessionClient";

export async function inviteCityResident(slug, username) {
  return (
    await sessionPost(`/cities/${encodeURIComponent(slug)}/invitations`, {
      username,
    })
  ).data;
}
export async function getSentCityInvitations(slug, page = 1) {
  return (
    await sessionGet(`/cities/${encodeURIComponent(slug)}/invitations`, {
      page,
    })
  ).data;
}
export async function revokeCityInvitation(slug, invitation_id) {
  return (
    await sessionDelete(
      `/cities/${encodeURIComponent(slug)}/invitations/${invitation_id}`,
    )
  ).data;
}
export async function getMyCityInvitations(page = 1) {
  return (await sessionGet("/account/city-invitations", { page })).data;
}
export async function respondCityInvitation(invitation_id, decision) {
  return (
    await sessionPost(`/account/city-invitations/${invitation_id}`, {
      decision,
    })
  ).data;
}
