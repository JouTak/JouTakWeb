import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import ProjectsSection from "./ProjectsSection.jsx";

describe("ProjectsSection", () => {
  it("renders BFF project data as navigation cards", () => {
    render(
      <MemoryRouter>
        <ProjectsSection
          projects={[
            {
              title: "Тестовый проект",
              description: `Бла-бла-бла, бле-бле-бле, блю-блю-блю`,
              image: "/img/cool.png",
              imageHeight: "248px",
              to: "/nevada",
            },
          ]}
        />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("link", { name: /тестовый проект/i }),
    ).toHaveAttribute("href", "/nevada");
    expect(
      screen.getByRole("img", { name: /тестовый проект/i }),
    ).toHaveAttribute("src", "/img/cool.png");
  });
});
