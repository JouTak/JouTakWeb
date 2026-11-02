import {
  sessionDelete,
  sessionGet,
  sessionPatch,
  sessionPost,
} from "../auth/sessionClient";

export async function getCities(params = {}) {
  return (await sessionGet("/cities", params, { hardLogoutOn401: false })).data;
}
export async function getCity(slug) {
  return (
    await sessionGet(`/cities/${encodeURIComponent(slug)}`, undefined, {
      hardLogoutOn401: false,
    })
  ).data;
}
export async function saveCity(slug, payload) {
  return (await sessionPatch(`/cities/${encodeURIComponent(slug)}`, payload))
    .data;
}
export async function getCityMembers(slug, page = 1) {
  return (
    await sessionGet(`/cities/${encodeURIComponent(slug)}/members`, { page })
  ).data;
}
export async function getCityResidents(slug, page = 1) {
  return (
    await sessionGet(
      `/cities/${encodeURIComponent(slug)}/residents`,
      { page },
      { hardLogoutOn401: false },
    )
  ).data;
}
export async function getOwnCityMembership(slug) {
  return (await sessionGet(`/cities/${encodeURIComponent(slug)}/membership`))
    .data;
}
export async function parseCityMapLink(slug, url) {
  return (
    await sessionPost(`/cities/${encodeURIComponent(slug)}/map-location`, {
      url,
    })
  ).data;
}
export async function uploadCityImage(slug, file) {
  const data = new FormData();
  data.append("file", file);
  return (await sessionPost(`/cities/${encodeURIComponent(slug)}/images`, data))
    .data;
}
export async function updateCityMember(slug, membership_id, payload) {
  return (
    await sessionPatch(
      `/cities/${encodeURIComponent(slug)}/members/${membership_id}`,
      payload,
    )
  ).data;
}
export async function removeCityMember(slug, membership_id) {
  return (
    await sessionDelete(
      `/cities/${encodeURIComponent(slug)}/members/${membership_id}`,
    )
  ).data;
}
export async function getCityHistory(slug, page = 1) {
  return (
    await sessionGet(`/cities/${encodeURIComponent(slug)}/history`, { page })
  ).data;
}

export async function saveMembershipVisibility(slug, visibility) {
  return (
    await sessionPatch(`/cities/${encodeURIComponent(slug)}/membership`, {
      visibility,
    })
  ).data;
}
