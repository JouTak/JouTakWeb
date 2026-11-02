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

import CityDetail from "../../pages/cities/CityDetail";
import { getCity, getCityHistory } from "../../services/api/citiesApi";
import {
  getMyCityInvitations,
  respondCityInvitation,
} from "../../services/api/cityInvitationsApi";
import CityInvitations from "./CityInvitations";
vi.mock("../../services/api/citiesApi", () => ({
  getCity: vi.fn(),
  getCityHistory: vi.fn(),
  getCityResidents: vi.fn(),
  saveCity: vi.fn(),
  uploadCityImage: vi.fn(),
  parseCityMapLink: vi.fn(),
}));
vi.mock("../../services/api/cityInvitationsApi", () => ({
  getMyCityInvitations: vi.fn(),
  respondCityInvitation: vi.fn(),
}));
const city = {
  slug: "alpha",
  name: "Альфа",
  description: "Текст",
  short_description: "У реки",
  status: "active",
  recruitment_status: "open",
  member_count: 1,
  leadership: [],
  contacts: [],
  community: { slug: "itmocraft", name: "ItmoCraft" },
  capabilities: { edit: true, manage_members: false },
  version: 1,
};
function show(node) {
  return render(
    <ThemeProvider theme="dark">
      <ToasterProvider toaster={new Toaster()}>
        <RouterProvider
          router={createMemoryRouter(
            [{ path: "/cities/:slug", element: node }],
            { initialEntries: ["/cities/alpha"] },
          )}
        />
      </ToasterProvider>
    </ThemeProvider>,
  );
}
describe("Contextual city workflow", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(cleanup);
  it("loads history only when its tab is opened", async () => {
    getCity.mockResolvedValue(city);
    getCityHistory.mockResolvedValue({ events: [], revisions: [], page: 1 });
    show(<CityDetail />);
    await screen.findByRole("heading", { name: "Альфа" });
    expect(getCityHistory).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("link", { name: "История" }));
    await waitFor(() =>
      expect(getCityHistory).toHaveBeenCalledWith("alpha", 1),
    );
  });
  it("opens a focused editor and keeps a dirty draft when cancelling close", async () => {
    getCity.mockResolvedValue(city);
    show(<CityDetail />);
    await screen.findByRole("heading", { name: "Альфа" });
    fireEvent.click(screen.getByRole("button", { name: "Изменить: о городе" }));
    expect(screen.queryByLabelText("Название")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Описание города"), {
      target: { value: "Черновик" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Закрыть", exact: true }),
    );
    expect(
      screen.getByText("Введённые изменения будут потеряны."),
    ).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Отмена", exact: true }),
    );
    expect(screen.getByLabelText("Описание города")).toHaveValue("Черновик");
  });
  it("does not accept an invitation until the recipient chooses to", async () => {
    getMyCityInvitations.mockResolvedValue({
      items: [{ id: 5, city_slug: "alpha", city_name: "Альфа" }],
      total: 1,
      page: 1,
    });
    respondCityInvitation.mockResolvedValue({ status: "accepted" });
    const changed = vi.fn();
    show(<CityInvitations onChanged={changed} />);
    await screen.findByText("Вас пригласили стать жителем.");
    expect(respondCityInvitation).not.toHaveBeenCalled();
    fireEvent.click(
      screen.getByRole("button", { name: "Принять приглашение" }),
    );
    await waitFor(() =>
      expect(respondCityInvitation).toHaveBeenCalledWith(5, "accept"),
    );
    expect(changed).toHaveBeenCalledOnce();
  });
});
