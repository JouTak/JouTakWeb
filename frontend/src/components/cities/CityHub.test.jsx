import { ThemeProvider, Toaster, ToasterProvider } from "@gravity-ui/uikit";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getCityMembers,
  removeCityMember,
  saveCity,
} from "../../services/api/citiesApi";
import MembershipCards from "../communities/MembershipCards";
import { ResourceState } from "../hub/HubShell";
import { Markdown } from "../hub/SafeContent";
import CityCard from "./CityCard";
import CityEditor from "./CityEditor";
import CityMapCard from "./CityMapCard";
import CityMembersManager from "./CityMembersManager";
import CityPresentation from "./CityPresentation";

vi.mock("../../services/api/citiesApi", () => ({
  saveCity: vi.fn(),
  getCityMembers: vi.fn(),
  removeCityMember: vi.fn(),
  parseCityMapLink: vi.fn(),
  uploadCityImage: vi.fn(),
  updateCityMember: vi.fn(),
  saveMembershipVisibility: vi.fn(),
}));
vi.mock("../../services/api/cityInvitationsApi", () => ({
  getSentCityInvitations: vi
    .fn()
    .mockResolvedValue({ items: [], total: 0, page: 1 }),
  inviteCityResident: vi.fn(),
  revokeCityInvitation: vi.fn(),
}));
const city = {
  slug: "alpha",
  name: "Альфа",
  short_description: "Город у реки",
  description: "Описание",
  community: { slug: "itmocraft", name: "ItmoCraft" },
  member_count: 3,
  recruitment_status: "open",
  status: "active",
  contacts: [],
  leadership: [],
  location: null,
  version: 1,
  capabilities: { edit: false, manage_members: false },
  updated_at: "2026-09-21T12:00:00Z",
};
const wrap = (node) =>
  render(
    <ThemeProvider theme="dark">
      <ToasterProvider toaster={new Toaster()}>
        <RouterProvider
          router={createMemoryRouter([{ path: "*", element: node }])}
        />
      </ToasterProvider>
    </ThemeProvider>,
  );

describe("Community hub", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(cleanup);
  it("shows useful city cards and no guest management", () => {
    wrap(
      <>
        <CityCard city={city} />
        <CityPresentation
          city={{
            ...city,
            leadership: [
              {
                username: "leader",
                minecraft_nick: "MayorCraft",
                display_name: "Имя Фамилия",
                role: "manager",
              },
              {
                username: "neighbor",
                display_name: "Личное имя",
                role: "representative",
              },
              { display_name: "Участник сообщества", role: "representative" },
            ],
          }}
        />
      </>,
    );
    expect(screen.getAllByText("Открыт для жителей")[0]).toBeDefined();
    expect(screen.queryByText("Управление")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "MayorCraft" })).toHaveAttribute(
      "href",
      "/u/leader",
    );
    expect(screen.getByRole("link", { name: "neighbor" })).toHaveAttribute(
      "href",
      "/u/neighbor",
    );
    expect(screen.getByText("Участник сообщества")).toBeInTheDocument();
    expect(screen.queryByText("Имя Фамилия")).not.toBeInTheDocument();
    expect(screen.queryByText("Личное имя")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Открыть Альфа" })).toHaveAttribute(
      "href",
      "/cities/alpha",
    );
    expect(
      screen.queryByRole("link", { name: "Подробнее →" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Набор открыт")).toBeInTheDocument();
    expect(screen.getByText("3 игрока")).toBeInTheDocument();
  });
  it("shows the mayor's nickname and a safe direct map link on the card", () => {
    wrap(
      <CityCard
        city={{
          ...city,
          member_count: 1,
          leader: {
            username: "mayor",
            minecraft_nick: "MayorCraft",
            position: "Мэр",
            display_name: "Личное имя",
          },
          map_url: "https://map.joutak.ru/#joutak:0:0:0:1500:0:0:0:1:flat",
        }}
      />,
    );
    expect(screen.getByRole("link", { name: "MayorCraft" })).toHaveAttribute(
      "href",
      "/u/mayor",
    );
    expect(screen.queryByText("Личное имя")).not.toBeInTheDocument();
    expect(screen.queryByText("ItmoCraft")).not.toBeInTheDocument();
    expect(screen.getByText("1 игрок")).toBeInTheDocument();
    const map = screen.getByRole("link", { name: "Альфа на карте" });
    expect(map).toHaveAttribute("target", "_blank");
    expect(map).toHaveAttribute("rel", "noopener noreferrer");
  });
  it("omits the catalog map shortcut without a safe URL", () => {
    wrap(<CityCard city={{ ...city, map_url: "javascript:alert(1)" }} />);
    expect(
      screen.queryByRole("link", { name: /на карте/ }),
    ).not.toBeInTheDocument();
  });
  it("shows map coordinates without requiring a URL", () => {
    render(<CityMapCard location={{ world: "overworld", x: 1240, z: -438 }} />);
    expect(screen.getByText("1240", { exact: false })).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
  it("opens canonical map links in an isolated tab", () => {
    render(
      <CityMapCard
        location={{
          world: "world",
          x: 0,
          z: 0,
          map_url: "https://map.joutak.ru/#joutak:0:0:0:1500:0:0:0:1:flat",
        }}
      />,
    );
    expect(screen.getByRole("link")).toHaveAttribute(
      "rel",
      "noopener noreferrer",
    );
  });
  it("renders account membership role and city relationship", () => {
    wrap(
      <MembershipCards
        own
        memberships={{
          communities: [],
          cities: [
            {
              ...city,
              role: "representative",
              position: "Дипломат",
              status: "active",
              visibility: "community",
              can_manage: true,
            },
          ],
        }}
      />,
    );
    expect(screen.getByText("Дипломат")).toBeInTheDocument();
    expect(screen.queryByText("Активное участие")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Альфа/ })).toHaveAttribute(
      "href",
      "/cities/alpha",
    );
  });
  it("omits archived cities from the current account overview", () => {
    wrap(
      <MembershipCards
        own
        memberships={{
          communities: [],
          cities: [
            {
              ...city,
              city_status: "archived",
              role: "manager",
              can_manage: false,
            },
          ],
        }}
      />,
    );
    expect(
      screen.queryByRole("heading", { name: "Альфа" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Альфа" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText("Кто видит моё членство"),
    ).not.toBeInTheDocument();
  });
  it("confirms removal and hides manager elevation from a manager", async () => {
    getCityMembers.mockResolvedValue({
      items: [
        {
          id: 7,
          username: "neighbor",
          minecraft_nick: "BuilderCraft",
          role: "resident",
          position: "",
        },
      ],
      total: 1,
      page: 1,
    });
    removeCityMember.mockResolvedValue({ ok: true });
    wrap(
      <CityMembersManager
        city={{
          ...city,
          capabilities: { manage_members: true, assign_manager: false },
        }}
      />,
    );
    await screen.findByText("BuilderCraft");
    fireEvent.click(
      screen.getByRole("button", { name: "Права @BuilderCraft" }),
    );
    expect(
      screen.queryByRole("option", { name: "Управляющий" }),
    ).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Исключить из города", exact: true }),
    );
    expect(removeCityMember).not.toHaveBeenCalled();
    expect(
      screen.getByText(/Участие и права в городе будут прекращены/),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Подтвердить" }));
    await waitFor(() =>
      expect(removeCityMember).toHaveBeenCalledWith("alpha", 7),
    );
  });
  it("shows errors and offers retry", () => {
    const reload = vi.fn();
    render(
      <ResourceState resource={{ error: new Error("offline"), reload }} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Повторить" }));
    expect(reload).toHaveBeenCalledOnce();
    expect(screen.getByRole("alert")).toHaveTextContent("offline");
  });
  it("does not render raw HTML or unsafe Markdown links", () => {
    const { container } = render(
      <Markdown>
        {
          "<script>alert(1)</script>\n\n[x](javascript:alert)\n\n<img src=x onerror=alert(1) />"
        }
      </Markdown>,
    );
    expect(container.querySelector("script,img,a")).toBeNull();
  });
  it("limits representative fields and preserves a failed edit", async () => {
    saveCity.mockRejectedValue({
      response: { data: { detail: "Версия изменилась" } },
    });
    wrap(
      <CityEditor
        city={{ ...city, capabilities: { edit: true, manage_location: false } }}
      />,
    );
    expect(screen.queryByLabelText("Мир")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Описание города"), {
      target: { value: "Новый текст" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Сохранить и опубликовать" }),
    );
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Версия изменилась"),
    );
    expect(screen.getByLabelText("Описание города")).toHaveValue("Новый текст");
    expect(saveCity).toHaveBeenCalledWith("alpha", {
      version: 1,
      description: "Новый текст",
    });
  });
});
