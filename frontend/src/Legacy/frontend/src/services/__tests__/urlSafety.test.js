import { describe, expect, it, vi } from "vitest";

vi.mock("../http/client", () => ({
  BACKEND_ROOT_URL: "https://api.example.test",
}));

import { BACKEND_ROOT_URL } from "../http/client";
import { sanitizeUrl } from "../urlSafety";

describe("sanitizeUrl", () => {
  it("allows backend-relative urls", () => {
    expect(sanitizeUrl("/oauth/link")).toBe(`${BACKEND_ROOT_URL}/oauth/link`);
  });

  it("rejects dangerous and unknown absolute urls", () => {
    expect(sanitizeUrl("javascript:alert(1)")).toBe("");
    expect(sanitizeUrl("JAVASCRIPT:alert(1)")).toBe("");
    expect(sanitizeUrl("data:text/html,alert")).toBe("");
    expect(sanitizeUrl("vbscript:msgbox")).toBe("");
    expect(sanitizeUrl("https://evil.example/path")).toBe("");
  });

  it("rejects protocol-relative and non-string inputs", () => {
    expect(sanitizeUrl("//evil.example/path")).toBe("");
    expect(sanitizeUrl("")).toBe("");
    expect(sanitizeUrl(null)).toBe("");
    expect(sanitizeUrl(undefined)).toBe("");
  });

  it("accepts absolute urls that match the backend origin", () => {
    const backendOrigin = new URL(BACKEND_ROOT_URL).origin;
    const target = `${backendOrigin}/accounts/yandex/login/?process=connect`;
    expect(sanitizeUrl(target)).toBe(target);
  });
});
