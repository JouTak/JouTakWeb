import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import ResponsiveMedia from "../ResponsiveMedia";

describe("ResponsiveMedia", () => {
  afterEach(cleanup);

  it("renders generated srcset, intrinsic dimensions and loading intent", () => {
    render(
      <ResponsiveMedia
        media={{
          kind: "asset",
          id: "itmocraft.hero.background",
          alt: "ITMOcraft",
        }}
        eager
        sizes="100vw"
      />,
    );

    const image = screen.getByRole("img", { name: "ITMOcraft" });
    expect(image).toHaveAttribute("loading", "eager");
    expect(image).toHaveAttribute("fetchpriority", "high");
    expect(image).toHaveAttribute("width", "1920");
    expect(image).toHaveAttribute("height", "1080");
    expect(document.querySelector("source")).toHaveAttribute("sizes", "100vw");
    expect(document.querySelector("source").srcset).toContain("480w");
    expect(document.querySelector("source").srcset).toContain("1920w");
  });

  it("preserves an allowlisted broken design placeholder", () => {
    const { container } = render(
      <ResponsiveMedia
        media={{
          kind: "design_placeholder",
          id: "gallery-photo",
          alt: "Placeholder",
          broken: true,
        }}
      />,
    );

    expect(container.querySelector("picture")).toHaveAttribute(
      "data-design-placeholder",
      "gallery-photo",
    );
    expect(screen.getByRole("img")).toHaveAttribute(
      "src",
      "/__design-placeholder__/gallery-photo",
    );
  });
});
