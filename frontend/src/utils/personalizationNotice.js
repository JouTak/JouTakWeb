const SEEN_KEY_PREFIX = "joutak_personalization_seen:";
const SIGNUP_SESSION_FLAG = "joutak_post_signup_personalization";

/**
 * Derive a stable key to track whether the user has seen the personalization
 * notice. Uses user ID so each user is tracked independently in localStorage.
 */
export function getPersonalizationNoticeKey(profile) {
  const userId = profile?.id || profile?.username || "anonymous";
  return `${SEEN_KEY_PREFIX}${userId}`;
}

/**
 * Whether the current session was created by a fresh signup (the signup
 * flow marks it before redirecting to the personalization wizard).
 */
export function isPostSignupPersonalizationSession(_profile) {
  try {
    return sessionStorage.getItem(SIGNUP_SESSION_FLAG) === "1";
  } catch {
    return false;
  }
}

/**
 * Mark the session as a post-signup personalization session (called during
 * the signup flow before redirecting to the personalization wizard).
 */
export function markPostSignupPersonalizationSession() {
  try {
    sessionStorage.setItem(SIGNUP_SESSION_FLAG, "1");
  } catch {
    /* noop */
  }
}

/**
 * Check if the user has already dismissed the personalization notice.
 */
export function hasSeenPersonalizationNotice(profile) {
  const key = getPersonalizationNoticeKey(profile);
  try {
    return localStorage.getItem(key) === "1";
  } catch {
    return false;
  }
}

/**
 * Record that the user has seen/dismissed the personalization notice.
 */
export function markPersonalizationNoticeSeen(profile) {
  const key = getPersonalizationNoticeKey(profile);
  try {
    localStorage.setItem(key, "1");
  } catch {
    /* noop */
  }
}
