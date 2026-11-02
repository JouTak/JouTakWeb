export const PROFILE_CHANGED_EVENT = "joutak:profile-changed";
export function notifyProfileChanged() {
  window.dispatchEvent(new Event(PROFILE_CHANGED_EVENT));
}

// A draft must not be retried with a session belonging to another account.
export const profileWriteOptions = {
  rotateSessionTokenOn401: false,
  refreshAccessOn401: false,
};
