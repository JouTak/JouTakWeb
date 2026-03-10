function emailLocalPart(email = "") {
  const normalized = String(email || "").trim();
  if (!normalized) return "";
  const [localPart] = normalized.split("@");
  return localPart || normalized;
}

export function getProfileDisplayName(profile) {
  const first = String(profile?.first_name || "").trim();
  const last = String(profile?.last_name || "").trim();
  const fullName = [first, last].filter(Boolean).join(" ").trim();

  return (
    fullName ||
    String(profile?.minecraft_nick || "").trim() ||
    emailLocalPart(profile?.email) ||
    String(profile?.username || "").trim() ||
    "Гость"
  );
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
