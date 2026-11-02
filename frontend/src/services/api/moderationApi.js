import { sessionGet, sessionPost } from "../auth/sessionClient";

export async function getModerationCities(params = {}) {
  return (await sessionGet("/moderation/cities", params)).data;
}
export async function createCity(payload) {
  return (await sessionPost("/moderation/cities", payload)).data;
}
