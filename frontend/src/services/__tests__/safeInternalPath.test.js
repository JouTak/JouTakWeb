import { describe, expect, it } from "vitest";

import { safeInternalPath } from "../urlSafety";
describe("safe continuation", () => {
  it("preserves internal search and anchor", () =>
    expect(safeInternalPath("/cities/alpha?tab=residents#list")).toBe(
      "/cities/alpha?tab=residents#list",
    ));
  it.each([
    "https://evil.test",
    "//evil.test",
    "/\\evil.test",
    "/%5cevil.test",
    "/%2fevil.test",
    "/login?next=/login",
    "/session-expired",
    "/%00evil",
  ])("rejects unsafe destination %s", (value) =>
    expect(safeInternalPath(value, "/account")).toBe("/account"),
  );
});
