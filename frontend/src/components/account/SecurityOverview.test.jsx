import { ThemeProvider } from "@gravity-ui/uikit";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import SecurityOverview from "./SecurityOverview";

vi.mock("./EmailCard", () => ({
  default: () => (
    <label>
      Новый email
      <input />
    </label>
  ),
}));
vi.mock("./PasswordCard", () => ({
  default: () => (
    <label>
      Новый пароль
      <input type="password" />
    </label>
  ),
}));
vi.mock("./MfaCard", () => ({
  default: () => <p>Настройки аутентификатора</p>,
}));
vi.mock("./OauthCard", () => ({ default: () => <p>Внешние сервисы</p> }));
vi.mock("./SessionsCard", () => ({ default: () => <p>Это устройство</p> }));
vi.mock("./DeleteAccountCard", () => ({
  default: () => <p>Подтвердить удаление</p>,
}));
afterEach(cleanup);
function show(props = {}, path = "/account/security") {
  return render(
    <ThemeProvider theme="dark">
      <MemoryRouter initialEntries={[path]}>
        <SecurityOverview
          profile={{ username: "builder", has_2fa: true, oauth_providers: [] }}
          emailStatus={{ email: "builder@example.local", verified: true }}
          sessionsPayload={{ sessions: [] }}
          {...props}
        />
      </MemoryRouter>
    </ThemeProvider>,
  );
}
describe("Security overview", () => {
  it("shows security states without profile fields or open password forms", () => {
    show();
    expect(
      screen.getByRole("heading", { level: 1, name: "Безопасность" }),
    ).toBeVisible();
    expect(screen.getByText("builder@example.local")).toBeVisible();
    expect(screen.getByText("Включена")).toBeVisible();
    expect(screen.queryByLabelText("Новый пароль")).toBeNull();
    expect(screen.queryByText("Подтвердить удаление")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Изменить пароль" }));
    fireEvent.change(screen.getByLabelText("Новый пароль"), {
      target: { value: "draft" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Свернуть пароль" }));
    fireEvent.click(screen.getByRole("button", { name: "Изменить пароль" }));
    expect(screen.getByLabelText("Новый пароль")).toHaveValue("draft");
  });
  it("keeps a failed sessions request distinct from an empty list", () => {
    const retry = vi.fn();
    show({ sessionsPayload: null, onRetry: retry });
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Не удалось получить список устройств",
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Повторить загрузку устройств" }),
    );
    expect(retry).toHaveBeenCalledOnce();
    expect(screen.queryByText("Это устройство")).toBeNull();
  });
  it("opens linked accounts when returning from an external provider", () => {
    show({}, "/account/security#linked");
    expect(screen.getByText("Внешние сервисы")).toBeVisible();
  });
});
