export function isPersonalizedProfile(profile) {
  if (!profile) return false;
  if (profile?.profile_state === "personalized") return true;
  if (profile?.registration_completed === true) return true;
  if (profile?.profile_tier === "advanced") return true;
  return profile?.account_active === true;
}

export function needsPersonalization(profile) {
  if (!profile) return false;
  if (profile?.personalization_ui_enabled === false) return false;
  return !isPersonalizedProfile(profile);
}
