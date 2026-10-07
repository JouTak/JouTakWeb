import { ThemeProvider, Toaster, ToasterProvider } from "@gravity-ui/uikit";
import {
  act,
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import { me, updateProfile } from "../../services/api";
import ProfileCard from "../account/ProfileCard";

vi.mock("../../services/api", () => ({
  me: vi.fn(),
  updateProfile: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it("saves segmented profile choices and requires ISU for ITMO students", async () => {
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  const user = userEvent.setup();
  const toaster = new Toaster();
  const onUpdated = vi.fn();
  updateProfile.mockResolvedValue({ message: "Сохранено" });

  render(
    <ThemeProvider theme="dark">
      <ToasterProvider toaster={toaster}>
        <ProfileCard
          profile={{
            first_name: "Test",
            last_name: "User",
            vk_username: "testuser",
            minecraft_nick: "TestPlayer",
            minecraft_has_license: false,
            is_itmo_student: false,
            itmo_isu: "",
          }}
          onUpdated={onUpdated}
        />
      </ToasterProvider>
    </ThemeProvider>,
  );

  await user.click(screen.getByRole("button", { name: "Изменить" }));
  for (const name of ["Есть лицензия Minecraft?", "Вы студент ИТМО?"]) {
    await user.click(
      within(screen.getByRole("group", { name })).getByRole("radio", {
        name: "Да",
      }),
    );
  }
  expect(screen.getByRole("button", { name: "Сохранить" })).toBeDisabled();
  await user.type(screen.getByRole("textbox", { name: "Номер ИСУ" }), "123456");
  await user.click(screen.getByRole("button", { name: "Сохранить" }));

  await waitFor(() =>
    expect(updateProfile).toHaveBeenCalledWith(
      expect.objectContaining({
        minecraft_has_license: true,
        is_itmo_student: true,
        itmo_isu: "123456",
      }),
    ),
  );
  expect(onUpdated).toHaveBeenCalled();
  expect(toaster.has("name-save")).toBe(true);
  toaster.destroy();
});

it("updates displayed profile when the parent supplies new data", () => {
  const toaster = new Toaster();
  const card = (name) => (
    <ThemeProvider theme="dark">
      <ToasterProvider toaster={toaster}>
        <ProfileCard profile={{ first_name: name }} />
      </ToasterProvider>
    </ThemeProvider>
  );
  const { rerender } = render(card("Before"));
  expect(screen.getByText("Before")).toBeInTheDocument();
  rerender(card("After"));
  expect(screen.queryByText("Before")).not.toBeInTheDocument();
  expect(screen.getByText("After")).toBeInTheDocument();
  toaster.destroy();
});

it("ignores a fetch superseded by profile data from the parent", async () => {
  let resolveFetch;
  me.mockReturnValue(
    new Promise((resolve) => {
      resolveFetch = resolve;
    }),
  );
  const toaster = new Toaster();
  const card = (profile) => (
    <ThemeProvider theme="dark">
      <ToasterProvider toaster={toaster}>
        <ProfileCard profile={profile} />
      </ToasterProvider>
    </ThemeProvider>
  );
  const { rerender } = render(card(undefined));
  rerender(card({ first_name: "Current" }));
  await act(async () => resolveFetch({ first_name: "Stale" }));
  expect(screen.getByText("Current")).toBeInTheDocument();
  expect(screen.queryByText("Stale")).not.toBeInTheDocument();
  toaster.destroy();
});
