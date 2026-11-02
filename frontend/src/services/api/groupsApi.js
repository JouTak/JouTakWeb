import { sessionGet, sessionPatch, sessionPost } from "../auth/sessionClient";

const publicRead = { hardLogoutOn401: false };
export async function getGroups(params = {}) {
  return (await sessionGet("/groups", params, publicRead)).data;
}
export async function getGroup(slug) {
  return (
    await sessionGet(
      `/groups/${encodeURIComponent(slug)}`,
      undefined,
      publicRead,
    )
  ).data;
}
export async function createGroup(payload) {
  return (await sessionPost("/groups", payload)).data;
}
export async function saveGroup(slug, payload) {
  return (await sessionPatch(`/groups/${encodeURIComponent(slug)}`, payload))
    .data;
}
export async function changeGroupLifecycle(slug, payload) {
  return (
    await sessionPost(`/groups/${encodeURIComponent(slug)}/lifecycle`, payload)
  ).data;
}
export async function uploadGroupImage(slug, file) {
  const data = new FormData();
  data.append("file", file);
  return (await sessionPost(`/groups/${encodeURIComponent(slug)}/images`, data))
    .data;
}
export async function getGroupPeople(slug, page = 1) {
  return (
    await sessionGet(
      `/groups/${encodeURIComponent(slug)}/people`,
      { page },
      publicRead,
    )
  ).data;
}
export async function getGroupMembers(slug, params = {}) {
  return (
    await sessionGet(`/groups/${encodeURIComponent(slug)}/members`, params)
  ).data;
}
export async function joinGroup(slug, payload) {
  return (
    await sessionPost(`/groups/${encodeURIComponent(slug)}/join`, payload)
  ).data;
}
export async function leaveGroup(slug) {
  return (await sessionPost(`/groups/${encodeURIComponent(slug)}/leave`)).data;
}
export async function setGroupVisibility(slug, payload) {
  return (
    await sessionPatch(
      `/groups/${encodeURIComponent(slug)}/membership`,
      payload,
    )
  ).data;
}
export async function changeGroupRole(slug, member_id, payload) {
  return (
    await sessionPatch(
      `/groups/${encodeURIComponent(slug)}/members/${member_id}`,
      payload,
    )
  ).data;
}
export async function removeGroupMember(slug, member_id, payload) {
  return (
    await sessionPost(
      `/groups/${encodeURIComponent(slug)}/members/${member_id}/remove`,
      payload,
    )
  ).data;
}
export async function restrictGroupMember(slug, member_id, payload) {
  return (
    await sessionPost(
      `/groups/${encodeURIComponent(slug)}/members/${member_id}/restriction`,
      payload,
    )
  ).data;
}
export async function applyToGroup(slug, payload) {
  return (
    await sessionPost(`/groups/${encodeURIComponent(slug)}/requests`, payload)
  ).data;
}
export async function withdrawGroupRequest(slug, process_id) {
  return (
    await sessionPost(
      `/groups/${encodeURIComponent(slug)}/requests/${process_id}/withdraw`,
    )
  ).data;
}
export async function withdrawMyGroupRequest(process_id) {
  return (await sessionPost(`/account/group-requests/${process_id}/withdraw`))
    .data;
}
export async function reviewGroupRequest(slug, process_id, payload) {
  return (
    await sessionPost(
      `/groups/${encodeURIComponent(slug)}/requests/${process_id}/decision`,
      payload,
    )
  ).data;
}
export async function getGroupProcesses(slug, params = {}) {
  return (
    await sessionGet(`/groups/${encodeURIComponent(slug)}/processes`, params)
  ).data;
}
export async function inviteToGroup(slug, payload) {
  return (
    await sessionPost(
      `/groups/${encodeURIComponent(slug)}/invitations`,
      payload,
    )
  ).data;
}
export async function revokeGroupInvitation(slug, process_id) {
  return (
    await sessionPost(
      `/groups/${encodeURIComponent(slug)}/invitations/${process_id}/revoke`,
    )
  ).data;
}
export async function offerGroupLeadership(slug, payload) {
  return (
    await sessionPost(`/groups/${encodeURIComponent(slug)}/leadership`, payload)
  ).data;
}
export async function revokeGroupLeadership(slug, process_id) {
  return (
    await sessionPost(
      `/groups/${encodeURIComponent(slug)}/leadership/${process_id}/revoke`,
    )
  ).data;
}
export async function getGroupHistory(slug, page = 1) {
  return (
    await sessionGet(`/groups/${encodeURIComponent(slug)}/history`, { page })
  ).data;
}
export async function getMyGroups(params = {}) {
  return (await sessionGet("/account/groups", params)).data;
}
export async function getMyGroupProcesses(page = 1) {
  return (await sessionGet("/account/group-processes", { page })).data;
}
export async function respondGroupInvitation(process_id, payload) {
  return (
    await sessionPost(`/account/group-invitations/${process_id}`, payload)
  ).data;
}
export async function respondGroupLeadership(process_id, payload) {
  return (await sessionPost(`/account/group-leadership/${process_id}`, payload))
    .data;
}
export async function getProfileGroups(username, page = 1) {
  return (
    await sessionGet(
      `/profiles/public/${encodeURIComponent(username)}/groups`,
      { page },
      publicRead,
    )
  ).data;
}
export async function getModerationGroups(page = 1) {
  return (await sessionGet("/moderation/groups", { page })).data;
}
export async function moderateGroup(slug, payload) {
  return (
    await sessionPost(
      `/moderation/groups/${encodeURIComponent(slug)}/restriction`,
      payload,
    )
  ).data;
}
export async function recoverGroupLeadership(slug, payload) {
  return (
    await sessionPost(
      `/moderation/groups/${encodeURIComponent(slug)}/recovery`,
      payload,
    )
  ).data;
}
