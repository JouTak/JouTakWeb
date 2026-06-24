import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import HeroSection from "./HeroSection.jsx";

describe("HeroSection", () => {
  it("renders BFF hero actions", () => {
    render(
      <MemoryRouter>
        <HeroSection
          hero={{
            title: "Новая главная",
            primary_cta: { href: "https://example.com", label: "Заявка" },
            secondary_cta: { to: "/joutak/pay", label: "Оплата" },
          }}
        />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: "Новая главная" }),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Заявка" })).toHaveAttribute(
      "href",
      "https://example.com",
    );
    expect(screen.getByRole("link", { name: "Оплата" })).toHaveAttribute(
      "href",
      "/joutak/pay",
    );
  });
});
