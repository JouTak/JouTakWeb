import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

async function fixture(page, { mfaError = false } = {}) {
  const writes = [];
  const now = new Date().toISOString();
  const profile = {
    username: "builder",
    minecraft_nick: "BuilderCraft",
    email: "builder@example.local",
    email_verified: true,
    has_2fa: true,
    oauth_providers: ["github"],
    registration_completed: true,
    profile_complete: true,
    personalization_interstitial_enabled: false,
  };
  const sessions = [
    {
      id: "current",
      current: true,
      user_agent: "Mozilla/5.0 (X11; Linux x86_64) Chrome/140.0",
      last_seen: now,
    },
    {
      id: "other",
      current: false,
      user_agent: "Mozilla/5.0 (Android) Firefox/140.0",
      last_seen: now,
    },
  ];
  await page.addInitScript(() =>
    sessionStorage.setItem(
      "joutak_auth",
      JSON.stringify({ session_token: "e2e-security" }),
    ),
  );
  await page.route("http://127.0.0.1:8000/**", async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    let status = 200;
    let body = {};
    if (["POST", "PATCH", "DELETE"].includes(req.method()))
      writes.push({ path, method: req.method() });
    if (path === "/bff/bootstrap")
      body = {
        viewer: { is_authenticated: true, username: "builder" },
        features: { community_profiles_ui: true },
      };
    else if (path === "/api/auth/me" || path === "/api/account/profile")
      body = profile;
    else if (path === "/api/account/sessions") body = { sessions };
    else if (path === "/api/account/sessions/other")
      body = { id: "other", revoked_reason: "manual" };
    else if (path.endsWith("/account/email"))
      body = {
        data: [{ email: profile.email, primary: true, verified: true }],
      };
    else if (path.endsWith("/account/authenticators/totp"))
      body = {
        data: { enabled: true, authenticator: { last_used_at: 1790000000 } },
      };
    else if (path.endsWith("/account/authenticators")) {
      if (mfaError) {
        status = 503;
        mfaError = false;
        body = { detail: "Temporarily unavailable" };
      } else body = { data: [{ id: 1, type: "totp" }] };
    } else if (path === "/api/oauth/providers")
      body = {
        providers: [
          { id: "github", name: "GitHub" },
          { id: "discord", name: "Discord" },
        ],
      };
    else {
      status = 404;
      body = { detail: "Недоступно" };
    }
    await route.fulfill({
      status: req.method() === "OPTIONS" ? 204 : status,
      contentType: "application/json",
      headers: {
        "access-control-allow-origin": "http://127.0.0.1:4173",
        "access-control-allow-credentials": "true",
        "access-control-allow-headers": "*",
        "access-control-allow-methods": "GET,POST,PATCH,DELETE,OPTIONS",
      },
      body: JSON.stringify(body),
    });
  });
  return writes;
}

test("security overview shows actual states, fits mobile and opens focused settings", async ({
  page,
}) => {
  const writes = await fixture(page);
  await page.goto("/account/security");
  await expect(
    page.getByRole("heading", { level: 1, name: "Безопасность" }),
  ).toBeVisible();
  await expect(page.getByText("Это устройство", { exact: true })).toBeVisible();
  await expect(page.getByText("Подтверждена", { exact: true })).toBeVisible();
  await expect(page.getByText("Включена", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Подтвердить удаление" }),
  ).toHaveCount(0);
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
  await page.screenshot({
    path: "/tmp/hub-security-desktop.png",
    fullPage: true,
  });
  expect(
    (await new AxeBuilder({ page }).include(".hub-page").analyze()).violations,
  ).toEqual([]);
  await page
    .getByRole("button", { name: "Изменить пароль", exact: true })
    .click();
  await expect(
    page.getByRole("textbox", { name: "Текущий пароль" }),
  ).toBeVisible();
  await expect(
    page.locator('input[autocomplete="current-password"]'),
  ).toHaveAttribute("type", "password");
  await page.getByRole("button", { name: "Свернуть пароль" }).click();
  await page.getByRole("button", { name: "Настроить привязки" }).click();
  await expect(page.getByText("Подключён", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Подключить Discord" }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "/tmp/hub-security-mobile.png",
    fullPage: true,
  });
  expect(writes).toEqual([]);
});

test("ending a session requires confirmation and keeps the current device", async ({
  page,
}) => {
  const writes = await fixture(page);
  await page.goto("/account/security");
  await page
    .getByRole("button", { name: "Завершить сеанс Firefox · Android" })
    .click();
  await expect(
    page.getByText(
      "На отключённых устройствах потребуется войти заново. Текущий сеанс сохранится.",
    ),
  ).toBeVisible();
  expect(writes).toEqual([]);
  await page.getByRole("button", { name: "Отмена", exact: true }).click();
  expect(writes).toEqual([]);
  await page
    .getByRole("button", { name: "Завершить сеанс Firefox · Android" })
    .click();
  await page.getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(
    page.getByText("Сессия завершена.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Завершить сеанс Firefox · Android" }),
  ).toHaveCount(0);
  await expect(page.getByText("Это устройство", { exact: true })).toBeVisible();
  expect(writes).toEqual([
    { path: "/api/account/sessions/other", method: "DELETE" },
  ]);
});

test("failed MFA status is retryable and does not offer setup as if disabled", async ({
  page,
}) => {
  await fixture(page, { mfaError: true });
  await page.goto("/account/security#mfa");
  await expect(page.getByRole("alert")).toContainText(
    "Не удалось проверить дополнительную защиту",
  );
  await expect(
    page.getByRole("button", { name: "Настроить", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Повторить проверку защиты" }).click();
  await expect(
    page.getByRole("button", { name: "Отключить аутентификатор" }),
  ).toBeVisible();
  for (const width of [320, 768]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
});
