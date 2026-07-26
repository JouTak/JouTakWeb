import { requestWithSession } from "../auth/sessionClient";
import { rootClient } from "../http/client";

export async function getPageDocument(route, { signal } = {}) {
  const response = await requestWithSession("get", route.endpoint, {
    client: rootClient,
    hardLogoutOn401: false,
    signal,
  });
  return response.data;
}
