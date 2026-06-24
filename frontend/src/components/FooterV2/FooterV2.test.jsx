import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import FooterV2 from "./FooterV2.jsx";

describe("FooterV2", () => {
  it("renders project navigation and external communities", () => {
    render(
      <MemoryRouter>
        <FooterV2 />
      </MemoryRouter>,
    );

    expect(screen.getByLabelText("JouTak")).toHaveAttribute("href", "/joutak");
    expect(screen.getByRole("link", { name: "Discord" })).toHaveAttribute(
      "target",
      "_blank",
    );
  });
});
