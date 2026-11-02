import {
  notifyProfileChanged,
  profileWriteOptions,
} from "../../features/hub/profileEvents";
import {
  sessionDelete,
  sessionGet,
  sessionPatch,
  sessionPost,
} from "../auth/sessionClient";

const publicRead = { hardLogoutOn401: false };
export async function findPlayers({
  q = "",
  page = 1,
  following = false,
} = {}) {
  return (
    await sessionGet("/profiles/players", { q, page, following }, publicRead)
  ).data;
}
export async function getConnections(
  username,
  direction = "following",
  page = 1,
) {
  return (
    await sessionGet(
      `/profiles/public/${encodeURIComponent(username)}/connections`,
      { direction, page },
      publicRead,
    )
  ).data;
}
export async function followPlayer(username) {
  return (
    await sessionPost(
      `/profiles/public/${encodeURIComponent(username)}/follow`,
      {},
    )
  ).data;
}
export async function unfollowPlayer(username) {
  return (
    await sessionDelete(
      `/profiles/public/${encodeURIComponent(username)}/follow`,
    )
  ).data;
}
export async function getProfileContacts() {
  return (await sessionGet("/profiles/me/contacts")).data;
}
export async function saveProfileContacts(payload) {
  const { data } = await sessionPatch(
    "/profiles/me/contacts",
    payload,
    profileWriteOptions,
  );
  notifyProfileChanged();
  return data;
}
export async function getOwnFollowing(page = 1) {
  return (await sessionGet("/profiles/me/following", { page })).data;
}
export async function removeOwnFollow(relation_id) {
  return (
    await sessionDelete(
      `/profiles/me/following/${relation_id}`,
      undefined,
      profileWriteOptions,
    )
  ).data;
}
