import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const community = { slug: "itmocraft", name: "ItmoCraft" };
const city = {
  slug: "alpha",
  name: "Альфа",
  community,
  short_description: "Город у реки",
  description: "Строим вместе.",
  logo_url: "",
  cover_url: "",
  status: "active",
  recruitment_status: "open",
  member_count: 3,
  leader: { username: "mayor", minecraft_nick: "MayorCraft", position: "Мэр" },
  map_url: "https://map.joutak.ru/#joutak:1240:0:-438:1500:0:0:0:1:flat",
  updated_at: "2026-09-21T09:00:00Z",
  version: 1,
  contacts: [],
  capabilities: { edit: false, manage_members: false },
  leadership: [
    {
      username: "mayor",
      display_name: "Алекс",
      minecraft_nick: "MayorCraft",
      role: "manager",
      position: "Мэр",
    },
  ],
  location: {
    world: "overworld",
    x: 1240,
    z: -438,
    map_url: "https://map.joutak.ru/#joutak:1240:0:-438:1500:0:0:0:1:flat",
  },
};
const features = {
  community_profiles_ui: true,
  communities_ui: true,
  cities_ui: true,
  cities_management_ui: true,
  cities_map_integration: true,
};
async function mockHub(page, enabled = true) {
  await page.route("http://127.0.0.1:8000/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let status = 200;
    let body = {};
    if (path === "/bff/bootstrap")
      body = {
        features: enabled ? features : {},
        viewer: { is_authenticated: false },
      };
    else if (path === "/api/profiles/players")
      body = {
        items: [
          {
            username: "mayor",
            display_name: "Алекс",
            bio: "Управляю городом",
            minecraft_nick: "MayorCraft",
            cities: [
              {
                slug: "alpha",
                name: "Альфа",
                role: "manager",
                position: "Мэр",
              },
            ],
          },
        ],
        total: 1,
        page: 1,
      };
    else if (path === "/api/cities")
      body = { items: [city], total: 1, page: 1 };
    else if (path === "/api/cities/alpha") body = city;
    else if (path === "/api/profiles/public/mayor/connections") {
      const direction = new URL(route.request().url()).searchParams.get(
        "direction",
      );
      body = {
        items: [
          {
            username: direction === "friends" ? "friend" : "follower",
            display_name: "Игрок",
          },
        ],
        total: 1,
        page: 1,
        is_visible: true,
      };
    } else if (path === "/api/profiles/public/mayor")
      body = {
        username: "mayor",
        display_name: "Алекс",
        minecraft_nick: "MayorCraft",
        bio: "Управляю городом",
        server_history: {
          first_joined_on: "2026-01-01",
          days: 263,
          days_text: "263 дня",
        },
        memberships: {
          communities: [],
          cities: [
            { ...city, role: "manager", position: "Мэр", status: "active" },
          ],
        },
      };
    else {
      status = 404;
      body = { detail: "Раздел недоступен", error_code: "NOT_FOUND" };
    }
    await route.fulfill({
      status: route.request().method() === "OPTIONS" ? 204 : status,
      contentType: "application/json",
      headers: {
        "access-control-allow-origin": "http://127.0.0.1:4173",
        "access-control-allow-credentials": "true",
        "access-control-allow-headers": "*",
      },
      body: JSON.stringify(body),
    });
  });
}

test("guest can follow city → profile → city and canonical map link", async ({
  page,
}) => {
  await mockHub(page);
  await page.goto("/cities");
  await expect(
    page.getByRole("link", { name: "Альфа на карте" }),
  ).toHaveAttribute("href", city.map_url);
  await page.getByRole("link", { name: "Альфа", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Альфа", level: 1 }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Управление", exact: true }),
  ).toHaveCount(0);
  const map = page.getByRole("link", { name: "Открыть в BlueMap ↗" });
  await expect(map).toHaveAttribute("href", city.location.map_url);
  await expect(map).toHaveAttribute("rel", "noopener noreferrer");
  await page.getByRole("link", { name: "MayorCraft", exact: true }).click();
  await expect(page.getByText("Управляю городом")).toBeVisible();
  await page.getByRole("link", { name: "Альфа — Мэр", exact: true }).click();
  await expect(map).toBeVisible();
});

test("profile cards and avatar grids are accessible at every breakpoint", async ({
  page,
}) => {
  await mockHub(page);
  for (const width of [320, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/u/mayor");
    await expect(
      page.getByRole("heading", { name: "Игрок уже 263 дня" }),
    ).toBeVisible();
    await expect(page.getByText("Алекс", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Друзья: 1")).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Профиль @friend" }),
    ).toHaveAttribute("href", "/u/friend");
    await expect(
      page.getByRole("link", { name: "Профиль @follower" }),
    ).toHaveAttribute("href", "/u/follower");
    await expect(page.getByRole("button", { name: "О человеке" })).toHaveCount(
      0,
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    const report = await new AxeBuilder({ page })
      .include(".hub-page")
      .analyze();
    expect(report.violations).toEqual([]);
  }
});

test("city is accessible and responsive on mobile, tablet and desktop", async ({
  page,
}) => {
  await mockHub(page);
  for (const width of [320, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/cities");
    await expect(page.getByText("Набор открыт")).toBeVisible();
    await expect(page.getByRole("link", { name: "MayorCraft" })).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    expect(
      (await new AxeBuilder({ page }).include(".hub-page").analyze())
        .violations,
    ).toEqual([]);
    await page.goto("/cities/alpha");
    await expect(
      page.getByRole("heading", { name: "Альфа", level: 1 }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    const report = await new AxeBuilder({ page })
      .include(".hub-page")
      .analyze();
    expect(report.violations).toEqual([]);
  }
});

test("disabled rollout hides city route", async ({ page }) => {
  await mockHub(page, false);
  await page.goto("/cities");
  await expect(
    page.getByRole("heading", { name: "Раздел пока недоступен" }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Подробнее →" })).toHaveCount(0);
});

test("players directory follows the profile design and works at every breakpoint", async ({
  page,
}) => {
  await mockHub(page);
  for (const width of [320, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/players");
    await expect(
      page.getByRole("heading", { name: "Игроки", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "MayorCraft", exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    const report = await new AxeBuilder({ page })
      .include(".hub-page")
      .analyze();
    expect(report.violations).toEqual([]);
  }
  await expect(
    page.getByRole("link", { name: "Альфа — Мэр", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "MayorCraft", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Алекс", { exact: true })).toHaveCount(0);
  await page.getByLabel("Имя, логин или ник Minecraft").fill("mayor");
  await page.getByRole("button", { name: "Найти", exact: true }).click();
  await expect(page).toHaveURL(/q=mayor/);
  await expect(
    page.getByRole("link", { name: "Войти и подписаться" }),
  ).toHaveCount(0);
  await page.getByRole("link", { name: "MayorCraft", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Войти и подписаться" }),
  ).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Подписаться/ })).toHaveCount(
    0,
  );
  await expect(
    page.getByRole("button", { name: "Поделиться профилем" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "MayorCraft", exact: true }),
  ).toBeVisible();
});
