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

import { HubContext } from "../../features/hub/context";
import OwnFollowing from "../../pages/profile/OwnFollowing";
import ProfilePreview from "../../pages/profile/ProfilePreview";
import * as people from "../../services/api/playersApi";
import * as api from "../../services/api/profilesApi";
import useResource from "../hub/useResource";
import GameDataEditor from "./GameDataEditor";
import ProfileEditor from "./ProfileEditor";
import ShareProfileButton from "./ShareProfileButton";

vi.mock("../../services/api/profilesApi", () => ({
  getSelfProfile: vi.fn(),
  saveCommunityProfile: vi.fn(),
  uploadProfileImage: vi.fn(),
  getGameData: vi.fn(),
  saveGameData: vi.fn(),
  getProfilePreview: vi.fn(),
  getPreviewConnections: vi.fn(),
  getPreviewGroups: vi.fn(),
}));
vi.mock("../../services/api/playersApi", () => ({
  getConnections: vi.fn(),
  getOwnFollowing: vi.fn(),
  removeOwnFollow: vi.fn(),
}));
const profile = {
  username: "builder",
  version: 3,
  display_name: "",
  bio: "До",
  avatar_url: "",
  visibility: "public",
  minecraft_visibility: "private",
  memberships: { cities: [], communities: [] },
};
function show(node) {
  return render(
    <ThemeProvider theme="dark">
      <ToasterProvider toaster={new Toaster()}>
        <RouterProvider
          router={createMemoryRouter([{ path: "*", element: node }], {
            initialEntries: ["/account/profile"],
          })}
        />
      </ToasterProvider>
    </ThemeProvider>,
  );
}
beforeEach(() => vi.resetAllMocks());
afterEach(cleanup);
describe("Profile editing", () => {
  it("sends only edited fields and adopts normalized values", async () => {
    api.saveCommunityProfile.mockResolvedValue({
      ...profile,
      version: 4,
      bio: "Мосты",
    });
    show(<ProfileEditor profile={profile} />);
    fireEvent.change(screen.getByLabelText("О себе"), {
      target: { value: "  Мосты  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить описание" }));
    await waitFor(() =>
      expect(api.saveCommunityProfile).toHaveBeenCalledWith({
        version: 3,
        bio: "  Мосты  ",
      }),
    );
    await waitFor(() =>
      expect(screen.getByLabelText("О себе")).toHaveValue("Мосты"),
    );
    expect(
      screen.getByRole("button", { name: "Сохранить описание" }),
    ).toBeDisabled();
  });
  it("preserves a conflicting draft and explicitly rebases only changed fields", async () => {
    api.saveCommunityProfile
      .mockRejectedValueOnce({
        response: {
          status: 409,
          data: { detail: "Изменено в другой вкладке" },
        },
      })
      .mockResolvedValue({
        ...profile,
        version: 5,
        bio: "Мой текст",
        visibility: "private",
      });
    api.getSelfProfile.mockResolvedValue({
      ...profile,
      version: 4,
      bio: "Свежий текст",
      visibility: "private",
    });
    show(<ProfileEditor profile={profile} />);
    fireEvent.change(screen.getByLabelText("О себе"), {
      target: { value: "Мой текст" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить описание" }));
    await screen.findByRole("alert");
    expect(screen.getByLabelText("О себе")).toHaveValue("Мой текст");
    fireEvent.click(
      screen.getByRole("button", { name: "Загрузить актуальные данные" }),
    );
    await screen.findByText("Сейчас сохранено: Свежий текст");
    fireEvent.click(
      screen.getByRole("button", { name: "Продолжить с моими изменениями" }),
    );
    expect(api.saveCommunityProfile).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Сохранить описание" }));
    await waitFor(() =>
      expect(api.saveCommunityProfile).toHaveBeenLastCalledWith({
        version: 4,
        bio: "Мой текст",
      }),
    );
  });
  it("keeps input after a network error", async () => {
    api.saveCommunityProfile.mockRejectedValue(new Error("Сеть недоступна"));
    show(<ProfileEditor profile={profile} />);
    fireEvent.change(screen.getByLabelText("О себе"), {
      target: { value: "Не потерять" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить описание" }));
    await screen.findByRole("alert");
    expect(screen.getByLabelText("О себе")).toHaveValue("Не потерять");
  });
  it("Minecraft editor never sends private neighbouring fields", async () => {
    api.saveGameData.mockResolvedValue({
      version: "v2",
      minecraft_nick: "NewCraft",
      minecraft_has_license: false,
    });
    show(
      <GameDataEditor
        profile={{
          version: "v1",
          minecraft_nick: "OldCraft",
          minecraft_has_license: false,
          vk_username: "private_vk",
          itmo_isu: "123456",
        }}
        section="game"
      />,
    );
    fireEvent.change(screen.getByLabelText("Ник Minecraft"), {
      target: { value: "NewCraft" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Сохранить", exact: true }),
    );
    await waitFor(() =>
      expect(api.saveGameData).toHaveBeenCalledWith({
        version: "v1",
        minecraft_nick: "NewCraft",
      }),
    );
  });
  it("renders the guest projection without owner actions or self fields", async () => {
    api.getProfilePreview.mockResolvedValue({
      profile: {
        ...profile,
        is_self: false,
        display_name: "",
        bio: "",
        server_history: null,
      },
    });
    api.getPreviewConnections.mockResolvedValue({
      is_visible: false,
      items: [],
      total: 0,
      page: 1,
    });
    show(<ProfilePreview />);
    await screen.findByRole("heading", { name: "builder" });
    expect(api.getSelfProfile).not.toHaveBeenCalled();
    expect(
      screen.queryByRole("link", { name: "Редактировать профиль" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Подписаться/ }),
    ).not.toBeInTheDocument();
    await screen.findAllByText("Список скрыт");
    expect(api.getPreviewConnections).toHaveBeenCalledWith(
      "builder",
      "friends",
      1,
    );
  });
  it("offers a scoped removal for a hidden followed profile", async () => {
    people.getOwnFollowing
      .mockResolvedValueOnce({
        items: [{ id: 12, profile: null }],
        total: 1,
        page: 1,
      })
      .mockResolvedValue({ items: [], total: 0, page: 1 });
    people.removeOwnFollow.mockResolvedValue({ is_following: false });
    show(<OwnFollowing />);
    await screen.findByText("Недоступный профиль");
    fireEvent.click(
      screen.getByRole("button", {
        name: "Отписаться от недоступного профиля",
      }),
    );
    await waitFor(() =>
      expect(people.removeOwnFollow).toHaveBeenCalledWith(12),
    );
    await screen.findByText("У вас пока нет подписок.");
  });
  it("clipboard fallback contains the canonical profile URL even in settings", async () => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockRejectedValue(new Error("denied")) },
    });
    show(<ShareProfileButton username="builder" />);
    fireEvent.click(
      screen.getByRole("button", { name: "Поделиться профилем" }),
    );
    expect(
      await screen.findByRole("textbox", { name: "Адрес профиля" }),
    ).toHaveValue(`${window.location.origin}/u/builder`);
  });
  it("does not render previous viewer data during an account switch", async () => {
    const load = vi
      .fn()
      .mockResolvedValueOnce({ secret: "First viewer" })
      .mockImplementation(() => new Promise(() => {}));
    function Sample() {
      const resource = useResource(load);
      return <div>{resource.data?.secret || "Loading"}</div>;
    }
    const view = render(
      <HubContext.Provider value={{ viewer: { username: "one" } }}>
        <Sample />
      </HubContext.Provider>,
    );
    await screen.findByText("First viewer");
    view.rerender(
      <HubContext.Provider value={{ viewer: { username: "two" } }}>
        <Sample />
      </HubContext.Provider>,
    );
    expect(screen.queryByText("First viewer")).not.toBeInTheDocument();
    expect(screen.getByText("Loading")).toBeInTheDocument();
  });
});
