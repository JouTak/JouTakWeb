import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import ProductActionsSection from "./ProductActionsSection.jsx";

describe("ProductActionsSection", () => {
  it("keeps external and internal product actions actionable", () => {
    render(
      <MemoryRouter>
        <ProductActionsSection
          eyebrow="JouTak SMP"
          title="Подключиться к серверу"
          description="Подай заявку и оплати доступ."
          facts={[
            { id: "server", label: "Адрес сервера", value: "mc.joutak.ru" },
          ]}
          items={[
            {
              id: "application",
              label: "Зарегистрироваться",
              href: "https://forms.example.test/application",
              external: true,
              disabled: false,
              emphasis: "primary",
            },
            {
              id: "payment",
              label: "Оплатить доступ",
              href: "/joutak/pay",
              external: false,
              disabled: false,
              emphasis: "secondary",
            },
          ]}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText("mc.joutak.ru")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Зарегистрироваться/ }),
    ).toHaveAttribute("target", "_blank");
    expect(
      screen.getByRole("link", { name: "Оплатить доступ" }),
    ).toHaveAttribute("href", "/joutak/pay");
  });
});
