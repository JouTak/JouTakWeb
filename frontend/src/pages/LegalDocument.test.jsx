import { ThemeProvider } from "@gravity-ui/uikit";
import {
  cleanup,
  render as renderWithoutTheme,
  screen,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import LegalDocument from "./LegalDocument.jsx";

vi.mock("../content/documents/documents", async (importOriginal) => {
  const original = await importOriginal();
  return {
    ...original,
    documents: {
      ...original.documents,
      privacy: {
        ...original.documents.privacy,
        versions: [
          ...original.documents.privacy.versions,
          {
            id: "2026-01-01",
            author: "Архивный автор",
            publishedAt: "2026-01-01",
            updatedAt: "2026-01-02",
            markdown: "## Архивный текст\n\nПервая редакция документа.",
          },
        ],
      },
    },
  };
});

function render(ui) {
  return renderWithoutTheme(<ThemeProvider theme="dark">{ui}</ThemeProvider>);
}

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
      expect(screen.getAllByText(/21 сентября 2026/)).toHaveLength(2);
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

it("opens an archived URL and switches the text and metadata back to current", async () => {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/privacy-policy?version=2026-01-01"]}>
      <LegalDocument documentType="privacy" />
    </MemoryRouter>,
  );
  expect(
    screen.getByRole("heading", { name: "Архивный текст" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Архивный автор")).toBeInTheDocument();
  await user.click(
    screen.getByRole("combobox", { name: "Редакция документа" }),
  );
  await user.click(screen.getByRole("option", { name: "2026-09-21" }));
  expect(screen.getByText("Команда JouTak")).toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "Архивный текст" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText(/макет/i)).not.toBeInTheDocument();
});

it("does not silently substitute the current document for an unknown version", async () => {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/privacy-policy?version=missing"]}>
      <LegalDocument documentType="privacy" />
    </MemoryRouter>,
  );
  expect(screen.getByRole("status")).toHaveTextContent(
    "Такая редакция документа не найдена",
  );
  expect(screen.queryByText(/Lorem ipsum/)).not.toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: "Открыть текущую редакцию" }),
  );
  expect(screen.getByRole("article")).toHaveTextContent("Lorem ipsum");
});
