import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import LegalDocument from "./LegalDocument.jsx";

afterEach(cleanup);

describe("LegalDocument", () => {
  it.each([
    ["privacy", "Политика конфиденциальности"],
    ["terms", "Условия использования"],
  ])("renders an honest pending state for %s", (documentType, title) => {
    render(
      <MemoryRouter>
        <LegalDocument documentType={documentType} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "нет утверждённого юридического текста",
    );
    expect(
      screen.getByRole("button", { name: "На главную ITMOcraft" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Связаться с нами" }),
    ).toBeInTheDocument();
  });
});
