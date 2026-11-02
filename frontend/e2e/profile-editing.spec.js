import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

async function fixture(
  page,
  { privateProfile = false, conflict = false } = {},
) {
  let profile = {
    username: "builder",
    version: 1,
    display_name: "Алексей",
    bio: "Строю мосты",
    avatar_url: "",
    visibility: "public",
    minecraft_nick: "OldCraft",
    memberships: { communities: [], cities: [] },
    is_self: true,
    minecraft_visibility: "private",
    connections_visibility: "public",
  };
  let game = {
    username: "builder",
    version: "2026-09-21T00:00:00.123456+00:00",
    minecraft_nick: "OldCraft",
    minecraft_has_license: false,
    vk_username: "private_vk",
    is_itmo_student: false,
    itmo_isu: "",
  };
  const writes = [];
  const reads = [];
  await page.addInitScript(() =>
    sessionStorage.setItem(
      "joutak_auth",
      JSON.stringify({ session_token: "e2e-profile-session" }),
    ),
  );
  await page.route("http://127.0.0.1:8000/**", async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    let body = {};
    let status = 200;
    reads.push(path);
    if (req.method() === "PATCH") {
      const data = req.postDataJSON();
      writes.push({ path, data });
      if (path === "/api/profiles/me" && conflict) {
        profile = {
          ...profile,
          version: 2,
          visibility: "private",
          bio: "Другой текст",
        };
        conflict = false;
        status = 409;
        body = {
          detail: "Профиль изменён в другой вкладке",
          error_code: "PROFILE_VERSION_CONFLICT",
        };
      } else if (path === "/api/profiles/me") {
        profile = {
          ...profile,
          ...data,
          bio: data.bio?.trim() ?? profile.bio,
          version: profile.version + 1,
        };
        body = profile;
      } else if (path === "/api/profiles/me/game-data") {
        game = {
          ...game,
          ...data,
          version: "2026-09-21T00:01:00.123456+00:00",
        };
        profile = { ...profile, minecraft_nick: game.minecraft_nick };
        body = game;
      }
    } else if (path === "/bff/bootstrap")
      body = {
        viewer: { is_authenticated: true, username: "builder" },
        features: {
          community_profiles_ui: true,
          player_connections_ui: true,
          player_groups_ui: true,
          communities_ui: true,
        },
      };
    else if (path === "/api/auth/me" || path === "/api/account/profile")
      body = {
        username: "builder",
        minecraft_nick: game.minecraft_nick,
        email: "builder@example.local",
        is_active: true,
        registration_completed: true,
        profile_complete: true,
        is_profile_complete: true,
        personalization_interstitial_enabled: false,
      };
    else if (path === "/api/profiles/me") body = profile;
    else if (path === "/api/profiles/me/game-data") body = game;
    else if (path === "/api/profiles/me/contacts")
      body = { version: 1, contacts: [] };
    else if (path === "/api/profiles/me/preview")
      body = {
        profile: privateProfile
          ? null
          : {
              ...profile,
              is_self: false,
              minecraft_nick: null,
              display_name: "Алексей",
              contacts: [],
              server_history: null,
            },
      };
    else if (path === "/api/profiles/me/preview/connections")
      body = { items: [], total: 0, page: 1, is_visible: true };
    else if (path === "/api/profiles/me/preview/groups")
      body = { items: [], total: 0, page: 1 };
    else {
      status = 404;
      body = { detail: "Недоступно", error_code: "NOT_FOUND" };
    }
    await route.fulfill({
      status: req.method() === "OPTIONS" ? 204 : status,
      contentType: "application/json",
      headers: {
        "access-control-allow-origin": "http://127.0.0.1:4173",
        "access-control-allow-credentials": "true",
        "access-control-allow-headers": "*",
        "access-control-allow-methods": "GET,PATCH,OPTIONS",
      },
      body: JSON.stringify(body),
    });
  });
  return { writes, reads };
}

test("a stale editor retains its draft and saves only explicitly changed fields", async ({
  page,
}) => {
  const { writes } = await fixture(page, { conflict: true });
  await page.goto("/account/profile");
  await page
    .getByRole("button", { name: "Изменить имя, аватар и описание" })
    .click();
  const bio = page.getByRole("textbox", { name: "О себе", exact: true });
  await bio.fill("  Новый текст  ");
  await page.getByRole("button", { name: "Сохранить описание" }).click();
  await expect(page.getByRole("alert")).toContainText("другой вкладке");
  await expect(bio).toHaveValue("  Новый текст  ");
  await page
    .getByRole("button", { name: "Загрузить актуальные данные" })
    .click();
  await expect(page.getByText("Сейчас сохранено: Другой текст")).toBeVisible();
  await page
    .getByRole("button", { name: "Продолжить с моими изменениями" })
    .click();
  expect(writes).toHaveLength(1);
  await page.getByRole("button", { name: "Сохранить описание" }).click();
  await expect(bio).toHaveValue("Новый текст");
  expect(writes.map((w) => w.data)).toEqual([
    { version: 1, bio: "  Новый текст  " },
    { version: 2, bio: "  Новый текст  " },
  ]);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("guest preview uses guest projections and fits mobile and keyboard navigation", async ({
  page,
}) => {
  const { reads } = await fixture(page);
  await page.goto("/account/profile/preview");
  await expect(
    page.getByRole("heading", { level: 1, name: "builder" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Редактировать профиль" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Поделиться профилем" }),
  ).toHaveCount(0);
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
  const violations = (
    await new AxeBuilder({ page }).include(".hub-page").analyze()
  ).violations;
  expect(violations).toEqual([]);
  await page.getByRole("link", { name: "← Вернуться к настройкам" }).focus();
  await expect(
    page.getByRole("link", { name: "← Вернуться к настройкам" }),
  ).toBeFocused();
  expect(reads).toContain("/api/profiles/me/preview/connections");
  expect(reads).toContain("/api/profiles/me/preview/groups");
});

test("a private profile preview does not show the owner's identity", async ({
  page,
}) => {
  await fixture(page, { privateProfile: true });
  await page.goto("/account/profile/preview");
  await expect(
    page.getByRole("heading", { name: "Профиль недоступен гостю" }),
  ).toBeVisible();
  await expect(page.locator(".hub-page")).not.toContainText("OldCraft");
  await expect(page.locator(".hub-page")).not.toContainText("Строю мосты");
});

test("Minecraft changes refresh the own hero and keep neighbouring account fields out of the write", async ({
  page,
}) => {
  const { writes } = await fixture(page);
  await page.goto("/account/profile");
  await expect(
    page.getByText("Не студент ИТМО", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Изменить Minecraft" }).click();
  await page.getByLabel("Ник Minecraft", { exact: true }).fill("NewCraft");
  await page.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(page.getByRole("heading", { name: "NewCraft" })).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(writes).toEqual([
    {
      path: "/api/profiles/me/game-data",
      data: {
        version: "2026-09-21T00:00:00.123456+00:00",
        minecraft_nick: "NewCraft",
      },
    },
  ]);
});
