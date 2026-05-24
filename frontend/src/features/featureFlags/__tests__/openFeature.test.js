import { describe, expect, it } from "vitest";

import { toFlagConfiguration } from "../openFeature";

describe("toFlagConfiguration", () => {
  it("preserves boolean values for boolean flags", () => {
    expect(toFlagConfiguration({ site_footer_v2: true })).toEqual({
      site_footer_v2: {
        disabled: false,
        variants: {
          true: true,
        },
        defaultVariant: "true",
      },
    });
  });

  it("preserves string values for variant flags", () => {
    expect(toFlagConfiguration({ site_homepage_version: "v2" })).toEqual({
      site_homepage_version: {
        disabled: false,
        variants: {
          v2: "v2",
        },
        defaultVariant: "v2",
      },
    });
  });
});
