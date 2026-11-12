import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ErrorPageRoute } from "../ErrorPageRoute.jsx";

vi.mock("../../components/Layout", () => ({
  default: ({ children }) => <div data-testid="layout">{children}</div>,
}));

vi.mock("../NotFound.jsx", () => ({
  default: () => <div>Legacy 404</div>,
}));

vi.mock("../NotFoundV2.jsx", () => ({
  default: () => <div>New 404 V2</div>,
}));

vi.mock("../Forbidden.jsx", () => ({
  default: () => <div>New 403 Forbidden</div>,
}));

vi.mock("../Restricted.jsx", () => ({
  default: () => <div>New Restricted</div>,
}));

const mockUseBootstrapFeatures = vi.fn();
vi.mock("../../hooks/useBootstrapFeatures.js", () => ({
  useBootstrapFeatures: () => mockUseBootstrapFeatures(),
}));

afterEach(() => {
  cleanup();
});

describe("ErrorPageRoute", () => {
  it("renders legacy 404 inside Layout when site_404_page_ui is disabled", async () => {
    mockUseBootstrapFeatures.mockReturnValue({
      loading: false,
      features: { site_404_page_ui: false },
    });

    render(
      <MemoryRouter initialEntries={["/unknown"]}>
        <Routes>
          <Route path="*" element={<ErrorPageRoute type="404" />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Legacy 404")).toBeInTheDocument();
    expect(screen.getByTestId("layout")).toBeInTheDocument();
  });

  it("renders fullscreen NotFoundV2 without Layout when site_404_page_ui is enabled", async () => {
    mockUseBootstrapFeatures.mockReturnValue({
      loading: false,
      features: { site_404_page_ui: true },
    });

    render(
      <MemoryRouter initialEntries={["/unknown"]}>
        <Routes>
          <Route path="*" element={<ErrorPageRoute type="404" />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("New 404 V2")).toBeInTheDocument();
    expect(screen.queryByTestId("layout")).not.toBeInTheDocument();
  });

  it("redirects /403 to / when site_403_page_ui is disabled", async () => {
    mockUseBootstrapFeatures.mockReturnValue({
      loading: false,
      features: { site_403_page_ui: false },
    });

    render(
      <MemoryRouter initialEntries={["/403"]}>
        <Routes>
          <Route path="/" element={<div>Home Page</div>} />
          <Route path="/403" element={<ErrorPageRoute type="403" />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Home Page")).toBeInTheDocument();
  });

  it("renders fullscreen Forbidden and Restricted when site_403_page_ui is enabled", async () => {
    mockUseBootstrapFeatures.mockReturnValue({
      loading: false,
      features: { site_403_page_ui: true },
    });

    const { unmount } = render(
      <MemoryRouter initialEntries={["/403"]}>
        <Routes>
          <Route path="/403" element={<ErrorPageRoute type="403" />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("New 403 Forbidden")).toBeInTheDocument();
    expect(screen.queryByTestId("layout")).not.toBeInTheDocument();
    unmount();

    render(
      <MemoryRouter initialEntries={["/restricted"]}>
        <Routes>
          <Route
            path="/restricted"
            element={<ErrorPageRoute type="restricted" />}
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("New Restricted")).toBeInTheDocument();
  });
});
