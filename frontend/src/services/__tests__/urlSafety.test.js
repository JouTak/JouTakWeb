import { describe, expect, it } from "vitest";

import { BACKEND_ROOT_URL } from "../http/client";
import { sanitizeUrl } from "../urlSafety";

describe("sanitizeUrl", () => {
  it("allows backend-relative urls", () => {
    expect(sanitizeUrl("/oauth/link")).toBe(`${BACKEND_ROOT_URL}/oauth/link`);
  });

  it("rejects dangerous and unknown absolute urls", () => {
    expect(sanitizeUrl("javascript:alert(1)")).toBe("");
    expect(sanitizeUrl("https://evil.example/path")).toBe("");
  });
});
