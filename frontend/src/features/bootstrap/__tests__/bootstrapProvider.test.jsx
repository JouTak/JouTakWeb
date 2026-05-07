import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import JouTak from "../../../pages/JouTak.jsx";
import { BootstrapProvider } from "../BootstrapProvider.jsx";

vi.mock("@openfeature/react-sdk", () => ({
  OpenFeatureProvider: ({ children }) => children,
  InMemoryProvider: class {
    async putConfiguration() {}
  },
  OpenFeature: {
    setProvider: vi.fn(),
  },
  useStringFlagValue: vi.fn((_, fallback) => fallback),
}));

vi.mock("../../../services/api/bffApi", () => ({
  getBootstrap: vi.fn(),
  getHomepagePayload: vi.fn(),
  pickFeatureOverrideParams: vi.fn(() => new URLSearchParams()),
}));

const { getBootstrap, getHomepagePayload } = await import(
  "../../../services/api/bffApi"
);

describe("BootstrapProvider", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("blocks variant-sensitive render until bootstrap resolves", async () => {
    let resolveBootstrap;
    getBootstrap.mockReturnValue(
      new Promise((resolve) => {
        resolveBootstrap = resolve;
      }),
    );
    getHomepagePayload.mockResolvedValue({
      variant: "legacy",
      content: {
        hero: {
          title: "JouTak",
          description: "Legacy content",
        },
        carousel: [],
      },
    });

    render(
      <MemoryRouter>
        <BootstrapProvider>
          <JouTak />
        </BootstrapProvider>
      </MemoryRouter>,
    );

    expect(screen.getByText("Загрузка...")).toBeInTheDocument();

    resolveBootstrap({
      viewer: { is_authenticated: false },
      features: { site_homepage_version: "legacy" },
      experiments: { anonymous_id_present: true },
      layout: { homepage_variant: "legacy" },
    });

    expect(await screen.findByText("JouTak")).toBeInTheDocument();
  });

  it("renders legacy homepage when bootstrap resolves to legacy", async () => {
    getBootstrap.mockResolvedValue({
      viewer: { is_authenticated: false },
      features: { site_homepage_version: "legacy" },
      experiments: { anonymous_id_present: true },
      layout: { homepage_variant: "legacy" },
    });
    getHomepagePayload.mockResolvedValue({
      variant: "legacy",
      content: {
        hero: {
          title: "JouTak",
          description: "Legacy content",
          server_ip: "mc.joutak.ru",
          primary_cta: { href: "https://example.com", label: "Join" },
          secondary_cta: { to: "/joutak/pay", label: "Pay" },
        },
        carousel: [],
      },
    });

    render(
      <MemoryRouter>
        <BootstrapProvider>
          <JouTak />
        </BootstrapProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Legacy content")).toBeInTheDocument();
  });

  it("renders v2 homepage when bootstrap resolves to v2", async () => {
    getBootstrap.mockResolvedValue({
      viewer: { is_authenticated: false },
      features: { site_homepage_version: "v2" },
      experiments: { anonymous_id_present: true },
      layout: { homepage_variant: "v2" },
    });
    getHomepagePayload.mockResolvedValue({
      variant: "v2",
      content: {
        hero: {
          title: "Новая главная",
          description: "V2 content",
          primary_cta: { href: "https://example.com", label: "Apply" },
          secondary_cta: { to: "/joutak/pay", label: "Pay" },
        },
        projects: [
          {
            title: "JouTak SMP",
            description: "Проект",
            path: "/joutak",
          },
        ],
        events: ["Event item"],
        gallery: ["https://example.com/image.png"],
        faq: [
          {
            question: "Зачем новая версия сайта?",
            answer: "Для rollout.",
          },
        ],
      },
    });

    render(
      <MemoryRouter>
        <BootstrapProvider>
          <JouTak />
        </BootstrapProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Новая главная")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("JouTak SMP")).toBeInTheDocument();
    });
  });
});
