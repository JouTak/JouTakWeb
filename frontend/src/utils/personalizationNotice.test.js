import { afterEach, describe, expect, it } from "vitest";

import {
  getPersonalizationNoticeKey,
  hasSeenPersonalizationNotice,
  isPostSignupPersonalizationSession,
  markPersonalizationNoticeSeen,
  markPostSignupPersonalizationSession,
  PERSONALIZATION_NOTICE_KEY_PREFIX,
} from "./personalizationNotice";

describe("personalization notice state", () => {
  afterEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it("uses stable profile identity for the storage key", () => {
    expect(getPersonalizationNoticeKey({ username: "User@Example.COM" })).toBe(
      `${PERSONALIZATION_NOTICE_KEY_PREFIX}user@example.com`,
    );
  });

  it("marks notice as seen for authenticated profiles", () => {
    const profile = { username: "player@example.com" };

    expect(hasSeenPersonalizationNotice(profile)).toBe(false);

    markPersonalizationNoticeSeen(profile);

    expect(hasSeenPersonalizationNotice(profile)).toBe(true);
  });

  it("does not persist notice state for guests", () => {
    markPersonalizationNoticeSeen(null);

    expect(hasSeenPersonalizationNotice(null)).toBe(false);
    expect(localStorage.length).toBe(0);
  });

  it("tracks post-signup suppression only in session storage", () => {
    const profile = { username: "new@example.com" };

    expect(isPostSignupPersonalizationSession(profile)).toBe(false);

    markPostSignupPersonalizationSession(profile);

    expect(isPostSignupPersonalizationSession(profile)).toBe(true);
    expect(hasSeenPersonalizationNotice(profile)).toBe(false);
  });
});
