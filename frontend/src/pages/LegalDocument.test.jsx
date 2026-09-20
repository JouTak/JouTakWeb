import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import LegalDocument from "./LegalDocument.jsx";

afterEach(cleanup);

describe("LegalDocument", () => {
  it.each([
    ["privacy", "Политика конфиденциальности"],
    ["terms", "Условия использования"],
  ])(
    "renders the document preview and publication metadata for %s",
    (documentType, title) => {
      render(
        <MemoryRouter>
          <LegalDocument documentType={documentType} />
        </MemoryRouter>,
      );

      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
      expect(screen.getByRole("article", { name: title })).toHaveTextContent(
        "Lorem ipsum",
      );
      expect(screen.getByText("Команда JouTak")).toBeInTheDocument();
      expect(screen.getAllByText("21 сентября 2026")).toHaveLength(2);
      expect(
        screen.getByRole("navigation", { name: "Содержание документа" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "На главную ITMOcraft" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Связаться с нами" }),
      ).toBeInTheDocument();
    },
  );
});
