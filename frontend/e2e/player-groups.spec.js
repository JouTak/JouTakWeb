import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const group = {
  slug: "builders",
  name: "Мастерская",
  short_description: "Строим и общаемся",
  description: "Место для совместных построек.",
  category: "club",
  scope: null,
  logo_url: "",
  cover_url: "",
  status: "active",
  access: "public",
  join_mode: "open",
  accepting: true,
  restricted: false,
  contacts: [],
  rules: "Берегите чужие постройки",
  welcome: "",
  application_question: "",
  roster_visibility: "members",
  version: 1,
};
async function fixture(page, { signedIn = false, invitation = false } = {}) {
  let joined = false;
  const writes = [];
  if (signedIn)
    await page.addInitScript(() =>
      sessionStorage.setItem(
        "joutak_auth",
        JSON.stringify({ session_token: "e2e-group-session" }),
      ),
    );
  await page.route("http://127.0.0.1:8000/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const isWrite = ["POST", "PATCH"].includes(request.method());
    if (isWrite) writes.push({ path, data: request.postDataJSON() });
    if (path.endsWith("/join") || path === "/api/account/group-invitations/9")
      joined = true;
    const member = joined
      ? {
          id: 1,
          status: "active",
          role: "member",
          visibility: "private",
          joined_at: "2026-09-21T10:00:00Z",
          eligible: true,
        }
      : null;
    const detail = {
      ...group,
      viewer: {
        state: joined ? "member" : signedIn ? "eligible" : "guest",
        membership: member,
      },
      capabilities: {
        join: signedIn && !joined,
        write_enabled: true,
        leave: joined,
      },
    };
    let body = {};
    let status = 200;
    if (path === "/bff/bootstrap")
      body = {
        viewer: { is_authenticated: signedIn, username: "builder" },
        features: {
          communities_ui: true,
          player_groups_ui: true,
          player_groups_write: true,
        },
      };
    else if (path === "/api/account/profile")
      body = {
        username: "builder",
        minecraft_nick: "BuilderCraft",
        profile_complete: true,
        is_profile_complete: true,
        personalization_interstitial_enabled: false,
      };
    else if (path === "/api/auth/me")
      body = {
        username: "builder",
        email: "builder@example.local",
        is_active: true,
        registration_completed: true,
        personalization_interstitial_enabled: false,
      };
    else if (path === "/api/communities")
      body = {
        items: [
          {
            slug: "itmocraft",
            name: "ItmoCraft",
            short_description: "Сервер",
            member_count: 3,
          },
        ],
        total: 1,
        page: 1,
      };
    else if (path === "/api/groups")
      body = { items: [group], total: 1, page: 1, can_create: signedIn };
    else if (
      path === "/api/groups/builders" ||
      path === "/api/groups/builders/join"
    )
      body = detail;
    else if (path === "/api/groups/builders/people")
      body = { items: [], total: null, is_visible: false, page: 1 };
    else if (path === "/api/account/server-communities") body = { items: [] };
    else if (path === "/api/account/groups")
      body = {
        items: joined ? [{ group, membership: member }] : [],
        total: joined ? 1 : 0,
        page: 1,
      };
    else if (path === "/api/account/group-processes")
      body = {
        items: invitation
          ? [
              {
                group,
                rules: group.rules,
                process: {
                  id: 9,
                  kind: "invitation",
                  status: joined ? "accepted" : "pending",
                  created_at: "2026-09-21T09:00:00Z",
                  expires_at: "2026-10-01T09:00:00Z",
                },
              },
            ]
          : [],
        total: invitation ? 1 : 0,
        page: 1,
        write_enabled: true,
      };
    else if (path === "/api/account/group-invitations/9")
      body = { status: "accepted" };
    else {
      status = 404;
      body = { detail: "Раздел недоступен", error_code: "NOT_FOUND" };
    }
    await route.fulfill({
      status: request.method() === "OPTIONS" ? 204 : status,
      contentType: "application/json",
      headers: {
        "access-control-allow-origin": "http://127.0.0.1:4173",
        "access-control-allow-credentials": "true",
        "access-control-allow-headers": "*",
      },
      body: JSON.stringify(body),
    });
  });
  return writes;
}

test("guest distinguishes server communities from clubs and opens the group", async ({
  page,
}) => {
  await fixture(page);
  await page.goto("/communities");
  await expect(
    page.getByRole("heading", { name: "Сообщества серверов" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Клубы и команды" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Создать объединение" }),
  ).toHaveCount(0);
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
  await page.getByRole("link", { name: /Мастерская/ }).click();
  await expect(
    page.getByRole("heading", { level: 1, name: "Мастерская" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Вступить", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: "Управление", exact: true }),
  ).toHaveCount(0);
});
test("joining and invitation acceptance require the recipient's action", async ({
  page,
}) => {
  const writes = await fixture(page, { signedIn: true, invitation: true });
  await page.goto("/account/communities");
  await expect(
    page.getByRole("button", { name: "Принять приглашение" }),
  ).toBeVisible();
  expect(writes).toEqual([]);
  await page.getByRole("button", { name: "Принять приглашение" }).click();
  await expect(
    page.getByText("Вы присоединились к объединению", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Принять приглашение" }),
  ).toHaveCount(0);
  expect(writes).toEqual([
    {
      path: "/api/account/group-invitations/9",
      data: { decision: "accept", visibility: "private" },
    },
  ]);
});
test("group page fits small screens and exposes labelled controls", async ({
  page,
}) => {
  await fixture(page, { signedIn: true });
  await page.goto("/groups/builders");
  await expect(
    page.getByRole("button", { name: "Вступить", exact: true }),
  ).toBeVisible();
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
  const results = await new AxeBuilder({ page }).include(".hub-page").analyze();
  expect(results.violations).toEqual([]);
  await page.getByLabel("Кто увидит моё участие").focus();
  await expect(page.getByLabel("Кто увидит моё участие")).toBeFocused();
});
