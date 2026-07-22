import { describe, expect, it } from "vitest";

import { extractErrorMessage } from "../errors";

describe("extractErrorMessage", () => {
  it("prefers detail and message fields", () => {
    expect(
      extractErrorMessage({ response: { data: { detail: "Detail" } } }),
    ).toBe("Detail");
    expect(
      extractErrorMessage({ response: { data: { message: "Message" } } }),
    ).toBe("Message");
  });

  it("reads flat and structured field errors", () => {
    expect(
      extractErrorMessage({
        response: { data: { fields: { email: "Invalid email" } } },
      }),
    ).toBe("Invalid email");
    expect(
      extractErrorMessage({
        response: {
          data: {
            errors: { password: [{ message: "Too weak", code: "weak" }] },
          },
        },
      }),
    ).toBe("Too weak");
  });

  it("prefers specific validation messages over generic detail", () => {
    expect(
      extractErrorMessage({
        response: {
          data: {
            detail: "validation_error",
            fields: { password: "Too short" },
          },
        },
      }),
    ).toBe("Too short");
  });

  it("falls back to the error message or provided fallback", () => {
    expect(extractErrorMessage(new Error("Network failed"))).toBe(
      "Network failed",
    );
    expect(extractErrorMessage({}, "Fallback")).toBe("Fallback");
  });
});
