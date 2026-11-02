import {
  notifyProfileChanged,
  profileWriteOptions,
} from "../../features/hub/profileEvents";
import { sessionGet, sessionPatch, sessionPost } from "../auth/sessionClient";

export async function uploadProfileImage(file) {
  const data = new FormData();
  data.append("file", file);
  return (await sessionPost("/profiles/images", data)).data;
}

export async function getSelfProfile() {
  return (await sessionGet("/profiles/me")).data;
}
export async function saveCommunityProfile(payload) {
  const { data } = await sessionPatch(
    "/profiles/me",
    payload,
    profileWriteOptions,
  );
  notifyProfileChanged();
  return data;
}

export async function getProfilePreview() {
  return (await sessionGet("/profiles/me/preview")).data;
}
export async function getPreviewConnections(_username, direction, page) {
  return (
    await sessionGet("/profiles/me/preview/connections", { direction, page })
  ).data;
}
export async function getPreviewGroups(_username, page) {
  return (await sessionGet("/profiles/me/preview/groups", { page })).data;
}
export async function getGameData() {
  return (await sessionGet("/profiles/me/game-data")).data;
}
export async function saveGameData(payload) {
  const { data } = await sessionPatch(
    "/profiles/me/game-data",
    payload,
    profileWriteOptions,
  );
  notifyProfileChanged();
  return data;
}
export async function getPublicProfile(username) {
  return (
    await sessionGet(
      `/profiles/public/${encodeURIComponent(username)}`,
      undefined,
      {
        hardLogoutOn401: false,
      },
    )
  ).data;
}
