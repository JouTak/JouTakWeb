import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import CustomFooter from "./Footer";

afterEach(cleanup);

describe("CustomFooter", () => {
  it("renders unfinished destinations as non-interactive design placeholders", () => {
    render(<CustomFooter />);

    expect(screen.getByRole("link", { name: "Контакты" })).toHaveAttribute(
      "href",
      "/contact",
    );
    expect(
      screen.getByRole("link", { name: "Политика конфиденциальности" }),
    ).toHaveAttribute("href", "/privacy-policy");
    expect(
      screen.getByRole("link", { name: "Условия использования" }),
    ).toHaveAttribute("href", "/terms-of-use");

    for (const label of ["Наша команда", "Документы"]) {
      expect(
        screen.queryByRole("link", { name: label }),
      ).not.toBeInTheDocument();
      expect(screen.getByText(label)).toHaveAttribute("aria-disabled", "true");
      expect(screen.getByText(label)).toHaveAttribute(
        "data-design-placeholder",
        "true",
      );
    }
  });

  it("links the ITMOcraft copyright to the canonical homepage", () => {
    render(<CustomFooter />);

    expect(screen.getByRole("link", { name: /Copyright/ })).toHaveAttribute(
      "href",
      "/",
    );
  });
});
