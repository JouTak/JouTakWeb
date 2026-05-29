import { describe, expect, it } from "vitest";

import { resolveBackendRoot } from "../http/client";

describe("resolveBackendRoot", () => {
  it("falls back to the local backend for unresolved runtime placeholders", () => {
    expect(resolveBackendRoot("__JOUTAK_RUNTIME_API_URL__")).toBe(
      "http://127.0.0.1:8000",
    );
  });

  it("falls back to the local backend for localhost without a backend port", () => {
    expect(resolveBackendRoot("http://localhost/")).toBe(
      "http://127.0.0.1:8000",
    );
  });

  it("preserves explicit backend origins", () => {
    expect(resolveBackendRoot("https://api.example.test/api/")).toBe(
      "https://api.example.test",
    );
    expect(resolveBackendRoot("https://api.example.test")).toBe(
      "https://api.example.test",
    );
  });
});
