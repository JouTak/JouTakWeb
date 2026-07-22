import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const hooks = vi.hoisted(() => ({
  useBooleanFlagValue: vi.fn((_, fallback) => fallback),
  useStringFlagValue: vi.fn((_, fallback) => fallback),
}));

vi.mock("@openfeature/react-sdk", () => hooks);

import FeatureGate from "../FeatureGate.jsx";

describe("FeatureGate", () => {
  it("uses a stable false fallback for inverted boolean gates", () => {
    render(
      <FeatureGate flag="site_footer_v2" expect={false}>
        <span>enabled</span>
      </FeatureGate>,
    );

    expect(screen.getByText("enabled")).toBeInTheDocument();
    expect(hooks.useBooleanFlagValue).toHaveBeenCalledWith(
      "site_footer_v2",
      false,
    );
  });

  it("routes variant gates through the string hook", () => {
    hooks.useStringFlagValue.mockImplementation(() => "v2");

    render(
      <FeatureGate flag="site_homepage_version" variant="v2">
        <span>v2</span>
      </FeatureGate>,
    );

    expect(screen.getByText("v2")).toBeInTheDocument();
    expect(hooks.useStringFlagValue).toHaveBeenCalledWith(
      "site_homepage_version",
      "",
    );
  });
});
