import {
  ThemeProvider,
  Toaster,
  ToasterComponent,
  ToasterProvider,
} from "@gravity-ui/uikit";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HubContext } from "../../features/hub/context";
import Players from "../../pages/profile/Players";
import {
  findPlayers,
  followPlayer,
  getConnections,
  saveProfileContacts,
  unfollowPlayer,
} from "../../services/api/playersApi";
import FollowButton from "./FollowButton";
import PlayerCard from "./PlayerCard";
import ProfileConnections from "./ProfileConnections";
import ProfileContactEditor from "./ProfileContactEditor";
import ProfileContacts, { CopyButton } from "./ProfileContacts";
import ShareProfileButton from "./ShareProfileButton";
vi.mock("../../services/api/playersApi", () => ({
  findPlayers: vi.fn(),
  followPlayer: vi.fn(),
  unfollowPlayer: vi.fn(),
  getConnections: vi.fn(),
  saveProfileContacts: vi.fn(),
  getProfileContacts: vi.fn(),
}));
const player = {
  username: "alex",
  display_name: "Алекс",
  bio: "Строю город",
  minecraft_nick: "AlexCraft",
  cities: [
    { slug: "alpha", name: "Альфа", role: "manager", position: "Мэр" },
    { slug: "beta", name: "Бета", role: "resident", position: "" },
  ],
  is_following: false,
};
function show(node, authenticated = true) {
  const router = createMemoryRouter([{ path: "*", element: node }], {
    initialEntries: ["/players"],
  });
  render(
    <ThemeProvider theme="dark">
      <ToasterProvider toaster={new Toaster()}>
        <HubContext.Provider
          value={{
            viewer: { is_authenticated: authenticated },
            flags: { community_profiles_ui: true },
          }}
        >
          <RouterProvider router={router} />
        </HubContext.Provider>
        <ToasterComponent />
      </ToasterProvider>
    </ThemeProvider>,
  );
  return router;
}
beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);
describe("Player connections", () => {
  it("searches on submit, preserves URL and links a result to its profile", async () => {
    findPlayers.mockResolvedValue({ items: [player], total: 1, page: 1 });
    const router = show(<Players />);
    await screen.findByText("Альфа — Мэр");
    fireEvent.change(screen.getByLabelText("Имя, логин или ник Minecraft"), {
      target: { value: "alex" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Найти", exact: true }));
    await waitFor(() =>
      expect(findPlayers).toHaveBeenLastCalledWith({
        q: "alex",
        page: 1,
        following: false,
      }),
    );
    expect(router.state.location.search).toBe("?q=alex");
    expect(
      screen.getByRole("link", { name: "AlexCraft", exact: true }),
    ).toHaveAttribute("href", "/u/alex");
  });
  it("follows and unfollows only after server success", async () => {
    followPlayer.mockResolvedValue({ is_following: true });
    unfollowPlayer.mockResolvedValue({ is_following: false });
    show(<FollowButton player={player} />);
    fireEvent.click(
      screen.getByRole("button", { name: "Подписаться на @AlexCraft" }),
    );
    await screen.findByRole("button", { name: "Отписаться от @AlexCraft" });
    expect(followPlayer).toHaveBeenCalledWith("alex");
    fireEvent.click(
      screen.getByRole("button", { name: "Отписаться от @AlexCraft" }),
    );
    await screen.findByRole("button", { name: "Подписаться на @AlexCraft" });
    expect(unfollowPlayer).toHaveBeenCalledWith("alex");
  });
  it("keeps unfollowed state when a request fails", async () => {
    followPlayer.mockRejectedValue(new Error("Попробуйте позже"));
    show(<FollowButton player={player} />);
    fireEvent.click(
      screen.getByRole("button", { name: "Подписаться на @AlexCraft" }),
    );
    await screen.findByRole("alert");
    expect(
      screen.getByRole("button", { name: "Подписаться на @AlexCraft" }),
    ).toBeInTheDocument();
  });
  it("offers guests a profile page without a sign-in or follow prompt", () => {
    show(<PlayerCard player={player} />, false);
    expect(
      screen.getByRole("link", { name: "AlexCraft", exact: true }),
    ).toHaveAttribute("href", "/u/alex");
    expect(
      screen.queryByRole("link", { name: "Войти и подписаться" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Подписаться/ }),
    ).not.toBeInTheDocument();
    expect(followPlayer).not.toHaveBeenCalled();
    expect(screen.queryByText("Алекс")).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "AlexCraft" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Строю город")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Альфа — Мэр" })).toHaveAttribute(
      "href",
      "/cities/alpha",
    );
    expect(screen.getByRole("link", { name: "Бета — Житель" })).toHaveAttribute(
      "href",
      "/cities/beta",
    );
  });
  it("explains a private circle without exposing counts", async () => {
    getConnections.mockResolvedValue({
      items: [],
      total: 0,
      is_visible: false,
    });
    show(<ProfileConnections username="alex" />);
    expect(await screen.findAllByText("Список скрыт")).toHaveLength(2);
    expect(screen.queryByText("0")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Пока нет доступных связей."),
    ).not.toBeInTheDocument();
  });
  it("adds contacts privately until the user changes visibility", async () => {
    saveProfileContacts.mockResolvedValue({
      version: 2,
      contacts: [{ type: "telegram", value: "alex", visibility: "private" }],
    });
    show(<ProfileContactEditor initial={{ version: 1, contacts: [] }} />);
    fireEvent.click(screen.getByRole("button", { name: "Добавить Telegram" }));
    fireEvent.change(screen.getByLabelText("Имя пользователя или ссылка"), {
      target: { value: "alex" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить контакты" }));
    await waitFor(() =>
      expect(saveProfileContacts).toHaveBeenCalledWith({
        version: 1,
        contacts: [{ type: "telegram", value: "alex", visibility: "private" }],
      }),
    );
  });
  it("shares only the supplied contact and handles unavailable clipboard", async () => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockRejectedValue(new Error("denied")) },
    });
    show(
      <>
        <ProfileContacts
          contacts={[
            { type: "telegram", value: "alex", url: "https://t.me/alex" },
          ]}
        />
        <CopyButton value="https://joutak.ru/u/alex">
          Скопировать адрес
        </CopyButton>
      </>,
    );
    expect(screen.getByRole("link", { name: "alex ↗" })).toHaveAttribute(
      "rel",
      "noopener noreferrer",
    );
    fireEvent.click(screen.getByRole("button", { name: "Скопировать адрес" }));
    await screen.findByText("https://joutak.ru/u/alex");
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      "https://joutak.ru/u/alex",
    );
  });
  it("shares a profile through an accessible icon without expanding its header", async () => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: vi
          .fn()
          .mockRejectedValue(new Error("denied"))
          .mockResolvedValueOnce(),
      },
    });
    show(<ShareProfileButton username="alex" />);
    const button = screen.getByRole("button", { name: "Поделиться профилем" });
    expect(button).toHaveTextContent("");
    fireEvent.click(button);
    await screen.findByText("Ссылка скопирована");
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      `${window.location.origin}/u/alex`,
    );
    fireEvent.click(button);
    expect(
      await screen.findByRole("textbox", { name: "Адрес профиля" }),
    ).toHaveValue(`${window.location.origin}/u/alex`);
    expect(
      screen.queryByText(`${window.location.origin}/u/alex`),
    ).not.toBeInTheDocument();
  });
});
