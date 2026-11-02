import { ThemeProvider, Toaster, ToasterProvider } from "@gravity-ui/uikit";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HubContext } from "../../features/hub/context";
import PublicProfile from "../../pages/profile/PublicProfile";
import { followPlayer, getConnections } from "../../services/api/playersApi";
import { getPublicProfile } from "../../services/api/profilesApi";

vi.mock("../../services/api/playersApi", () => ({
  getConnections: vi.fn(),
  followPlayer: vi.fn(),
  unfollowPlayer: vi.fn(),
}));
vi.mock("../../services/api/profilesApi", () => ({
  getPublicProfile: vi.fn(),
}));

const profile = {
  username: "alex",
  display_name: "Алекс",
  minecraft_nick: "AlexCraft",
  bio: "Строю город",
  contacts: [],
  memberships: { communities: [], cities: [] },
  server_history: {
    first_joined_on: "2026-01-01",
    days: 21,
    days_text: "21 день",
  },
};
const empty = { items: [], total: 0, page: 1, is_visible: true };
function show() {
  const router = createMemoryRouter(
    [{ path: "/u/:username", element: <PublicProfile /> }],
    { initialEntries: ["/u/alex"] },
  );
  render(
    <ThemeProvider theme="dark">
      <ToasterProvider toaster={new Toaster()}>
        <HubContext.Provider value={{ viewer: { is_authenticated: true } }}>
          <RouterProvider router={router} />
        </HubContext.Provider>
      </ToasterProvider>
    </ThemeProvider>,
  );
}
beforeEach(() => {
  vi.resetAllMocks();
  getPublicProfile.mockResolvedValue(profile);
  getConnections.mockResolvedValue(empty);
});
afterEach(cleanup);

describe("Profile cards", () => {
  it("shows name, server history and two avatar cards without tabs", async () => {
    getConnections.mockImplementation((_name, direction) =>
      Promise.resolve({
        ...empty,
        total: 1,
        items: [{ username: direction === "friends" ? "friend" : "follower" }],
      }),
    );
    show();
    await screen.findByRole("heading", { name: "Игрок уже 21 день" });
    expect(screen.getByText("Алекс")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "AlexCraft" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Редактировать профиль" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("01.01.2026")).toHaveAttribute(
      "datetime",
      "2026-01-01",
    );
    expect(screen.queryByText("О человеке")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Круг общения" }),
    ).not.toBeInTheDocument();
    const friends = screen.getByRole("region", { name: "Друзья" });
    expect(
      await within(friends).findByRole("link", { name: "Профиль @friend" }),
    ).toHaveAttribute("href", "/u/friend");
    expect(within(friends).getByLabelText("Друзья: 1")).toBeInTheDocument();
    const followers = screen.getByRole("region", { name: "Подписчики" });
    expect(
      within(followers).getByRole("link", { name: "Профиль @follower" }),
    ).toHaveAttribute("href", "/u/follower");
  });

  it("offers only the owner an accessible edit icon beside sharing", async () => {
    getPublicProfile.mockResolvedValue({ ...profile, is_self: true });
    show();
    const edit = await screen.findByRole("link", {
      name: "Редактировать профиль",
    });
    expect(edit).toHaveAttribute("href", "/account/profile");
    expect(edit).toHaveTextContent("");
    expect(edit.parentElement).toContainElement(
      screen.getByRole("button", { name: "Поделиться профилем" }),
    );
  });

  it("refreshes both cards after a successful reciprocal follow", async () => {
    let reciprocal = false;
    getConnections.mockImplementation((_name, direction) =>
      Promise.resolve({
        ...empty,
        total: (direction === "friends") === reciprocal ? 1 : 0,
      }),
    );
    followPlayer.mockImplementation(async () => {
      reciprocal = true;
      return { is_following: true };
    });
    show();
    await screen.findByLabelText("Подписчики: 1");
    expect(screen.getByLabelText("Друзья: 0")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Подписаться на @AlexCraft" }),
    );
    await screen.findByLabelText("Друзья: 1");
    expect(screen.getByLabelText("Подписчики: 0")).toBeInTheDocument();
    expect(getConnections).toHaveBeenCalledTimes(4);
  });

  it("retries a failed card without hiding the other card", async () => {
    getConnections.mockImplementation((_name, direction) =>
      direction === "followers"
        ? Promise.reject(new Error("Нет соединения"))
        : Promise.resolve(empty),
    );
    show();
    await screen.findByText("Нет соединения");
    expect(screen.getByLabelText("Друзья: 0")).toBeInTheDocument();
    getConnections.mockResolvedValue(empty);
    fireEvent.click(
      screen.getByRole("button", { name: "Повторить", exact: true }),
    );
    await waitFor(() =>
      expect(screen.getByLabelText("Подписчики: 0")).toBeInTheDocument(),
    );
  });
});
