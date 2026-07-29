import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import CustomFooter from "./Footer";

describe("CustomFooter", () => {
  it("renders unfinished destinations as non-interactive design placeholders", () => {
    render(<CustomFooter />);

    expect(screen.getByRole("link", { name: "Контакты" })).toHaveAttribute(
      "href",
      "/contact",
    );

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
});
