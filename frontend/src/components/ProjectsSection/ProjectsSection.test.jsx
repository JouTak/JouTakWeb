import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import ProjectsSection from "./ProjectsSection.jsx";

describe("ProjectsSection", () => {
  it("renders BFF project data as navigation cards", () => {
    render(
      <MemoryRouter>
        <ProjectsSection
          items={[
            {
              title: "ITMOcraft",
              description: "Minecraft community",
              path: "/itmocraft",
            },
          ]}
        />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: /ITMOcraft/ })).toHaveAttribute(
      "href",
      "/itmocraft",
    );
    expect(screen.getByRole("img", { name: "ITMOcraft" })).toHaveAttribute(
      "src",
      "/img/itmocraft.png",
    );
  });
});
