import { getPlayerName } from "./playerIdentity";

export function getProfileDisplayName(profile) {
  return profile ? getPlayerName(profile) : "Гость";
}

export function getProfileIdentityKey(profile) {
  return (
    String(profile?.email || "")
      .trim()
      .toLowerCase() ||
    String(profile?.username || "").trim() ||
    "guest"
  );
}
