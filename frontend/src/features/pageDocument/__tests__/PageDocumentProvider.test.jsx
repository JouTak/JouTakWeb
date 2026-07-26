import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { usePageDocument } from "../pageDocumentContext";
import { PageDocumentProvider } from "../PageDocumentProvider";

const { getPageDocument } = vi.hoisted(() => ({
  getPageDocument: vi.fn(),
}));

vi.mock("../../../services/api/pageApi", () => ({
  getPageDocument: (...args) => getPageDocument(...args),
}));

function documentFor(productId, variant = "legacy") {
  const paths = {
    itmocraft: "/",
    joutak: "/joutak",
    minigames: "/minigames",
  };
  return {
    schema_version: 1,
    product: {
      id: productId,
      canonical_path: paths[productId],
      requested_path: paths[productId],
      is_legacy_alias: false,
    },
    effective_page_variant: variant,
    variant_source: "default",
    layout: {
      header_variant: variant,
      footer_variant: variant,
      default_project: "itmo_craft",
    },
    viewer: { is_authenticated: false, profile_state: "guest" },
    content: { template: `landing-${variant}`, sections: [] },
  };
}

function Consumer() {
  const navigate = useNavigate();
  const { document, loading } = usePageDocument();
  return (
    <>
      <output>{loading ? "loading" : document?.product.id || "none"}</output>
      <button type="button" onClick={() => navigate("/joutak")}>
        JouTak
      </button>
    </>
  );
}

describe("PageDocumentProvider", () => {
  afterEach(() => {
    cleanup();
    getPageDocument.mockReset();
  });

  it("performs one product request and follows Router navigation", async () => {
    getPageDocument
      .mockResolvedValueOnce(documentFor("itmocraft"))
      .mockResolvedValueOnce(documentFor("joutak", "v2"));

    render(
      <MemoryRouter initialEntries={["/"]}>
        <PageDocumentProvider>
          <Consumer />
        </PageDocumentProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByText("itmocraft")).toBeInTheDocument();
    expect(getPageDocument).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "JouTak" }));

    expect(await screen.findByText("joutak")).toBeInTheDocument();
    expect(getPageDocument).toHaveBeenCalledTimes(2);
    expect(getPageDocument.mock.calls[1][0].endpoint).toBe("/bff/pages/joutak");
  });

  it("ignores a stale response after navigation", async () => {
    let resolveItmocraft;
    const stale = new Promise((resolve) => {
      resolveItmocraft = resolve;
    });
    getPageDocument
      .mockReturnValueOnce(stale)
      .mockResolvedValueOnce(documentFor("joutak", "v2"));

    render(
      <MemoryRouter initialEntries={["/"]}>
        <PageDocumentProvider>
          <Consumer />
        </PageDocumentProvider>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "JouTak" }));
    expect(await screen.findByText("joutak")).toBeInTheDocument();

    resolveItmocraft(documentFor("itmocraft"));
    await waitFor(() => {
      expect(screen.getByText("joutak")).toBeInTheDocument();
    });
  });
});
