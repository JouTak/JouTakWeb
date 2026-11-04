import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const ROUTES = [
  { path: "/", product: "itmocraft", legacyAlias: false },
  { path: "/itmocraft", product: "itmocraft", legacyAlias: true },
  { path: "/joutak", product: "joutak", legacyAlias: false },
  { path: "/minigames", product: "minigames", legacyAlias: false },
  { path: "/contact", product: "contact", legacyAlias: false },
];
const WIDTHS = [320, 375, 480, 768, 1024, 1440, 1920, 2560];

function asset(id, alt) {
  return { kind: "asset", id, alt };
}

function pageDocument({ path, product, legacyAlias }, variant = "v2") {
  const legacy = legacyAlias || variant === "legacy";
  return {
    schema_version: 1,
    product: {
      id: product,
      canonical_path: product === "itmocraft" ? "/" : `/${product}`,
      requested_path: path,
      is_legacy_alias: legacyAlias,
    },
    effective_page_variant: legacy ? "legacy" : "v2",
    variant_source: legacyAlias
      ? "fixed_legacy"
      : legacy
        ? "default"
        : "feature_flag",
    layout: {
      header_variant: legacyAlias ? variant : legacy ? "legacy" : "v2",
      footer_variant: legacyAlias ? variant : legacy ? "legacy" : "v2",
      default_project:
        product === "itmocraft"
          ? "itmo_craft"
          : product === "joutak"
            ? "jou_tak"
            : "mini_games",
    },
    viewer: {
      is_authenticated: true,
      username: "design-tester",
      email: "tester@example.com",
      profile_state: "complete",
      profile_complete: true,
      personalization_context: null,
    },
    content: {
      template: legacy ? "landing-legacy" : "landing-v2",
      sections:
        legacy || product === "contact"
          ? []
          : [
              {
                type: "hero",
                background: asset(
                  `${product}.hero.background`,
                  `${product} background`,
                ),
                logo: asset(`${product}.logo`, `${product} logo`),
                eyebrow: "Комьюнити",
                title: product,
                description: "Больше, чем просто сервер!",
                primary_action: null,
              },
              {
                type: "actions",
                eyebrow: "Доступ",
                title:
                  product === "minigames"
                    ? "Играть и участвовать"
                    : `Действия ${product}`,
                description:
                  "Проверяем, что основные пользовательские действия доступны на каждой ширине.",
                facts:
                  product === "joutak"
                    ? [
                        {
                          id: "server",
                          label: "Адрес сервера",
                          value: "mc.joutak.ru",
                        },
                      ]
                    : [],
                items: [
                  {
                    id: "primary-action",
                    label: "Основное действие",
                    emphasis: "primary",
                    action: {
                      kind: "external",
                      href: "https://example.com/action",
                    },
                  },
                  {
                    id: "secondary-action",
                    label: "Зарегистрироваться",
                    emphasis: "secondary",
                    action: { kind: "internal", path: "/contact" },
                  },
                ],
              },
              {
                type: "events",
                title: "События",
                items: [
                  {
                    id: "bunker",
                    title: "Бункер",
                    description: "Тестовое событие",
                    location: "Online",
                    image: asset("events.bunker", "Бункер"),
                    starts_at: "2026-08-01T18:00:00+03:00",
                    action: { kind: "internal", path: "/" },
                  },
                ],
              },
              {
                type: "gallery",
                title: "Галерея",
                items: [
                  {
                    id: "joutak",
                    label: "JouTak",
                    cover: asset("gallery.joutak.cover", "JouTak gallery"),
                    photos: [
                      {
                        kind: "design_placeholder",
                        id: "joutak-photo-1",
                        alt: "JouTak screenshot placeholder",
                        broken: true,
                      },
                      asset("gallery.joutak.cover", "JouTak gallery"),
                    ],
                  },
                ],
              },
              {
                type: "faq",
                title: "FAQ",
                items: [
                  {
                    id: "prototype",
                    question: "Что это?",
                    answer: "Прототип для согласования дизайна.",
                  },
                ],
              },
            ],
    },
  };
}

async function mockPageDocuments(page, { variant = "v2" } = {}) {
  await page.route("http://127.0.0.1:8000/bff/pages/**", async (route) => {
    const request = route.request();
    if (request.method() === "OPTIONS") {
      await route.fulfill({
        status: 204,
        headers: {
          "access-control-allow-origin": "http://127.0.0.1:4173",
          "access-control-allow-credentials": "true",
          "access-control-allow-headers": "*",
        },
      });
      return;
    }
    const pathname = new URL(request.url()).pathname;
    const routeSpec = pathname.endsWith("/itmocraft/legacy")
      ? ROUTES[1]
      : ROUTES.find(
          ({ product, legacyAlias }) =>
            !legacyAlias && pathname.endsWith(`/${product}`),
        );
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      headers: {
        "access-control-allow-origin": "http://127.0.0.1:4173",
        "access-control-allow-credentials": "true",
      },
      body: JSON.stringify(pageDocument(routeSpec, variant)),
    });
  });
}

test.beforeEach(async ({ page }) => {
  await mockPageDocuments(page);
});

for (const variant of ["legacy", "v2"]) {
  for (const width of WIDTHS) {
    test(`${variant} ${width}px routes have no overflow or header overlap`, async ({
      page,
    }) => {
      await page.unroute("http://127.0.0.1:8000/bff/pages/**");
      await mockPageDocuments(page, { variant });
      await page.setViewportSize({ width, height: 900 });
      for (const route of ROUTES) {
        await test.step(`${variant} ${width}px ${route.path}`, async () => {
          await page.goto(route.path, { waitUntil: "domcontentloaded" });
          if (route.product === "contact") {
            await expect(page.getByRole("heading", { level: 1 })).toHaveText(
              variant === "v2" ? "НАШИ КОНТАКТЫ" : "Наши сообщества",
            );
          } else if (variant === "v2" && !route.legacyAlias) {
            await expect(
              page.getByRole("link", { name: "Основное действие" }),
            ).toHaveAttribute("href", "https://example.com/action");
          } else if (route.product === "minigames") {
            await expect(
              page.getByRole("img", { name: "MiniGames Logo" }),
            ).toBeVisible();
          } else {
            await expect(
              page.getByRole("heading", {
                level: 1,
                name: route.product === "itmocraft" ? "ITMOcraft" : "JouTak",
                exact: true,
              }),
            ).toBeVisible();
          }
          await page.evaluate(() => document.fonts.ready);
          if (variant === "legacy") {
            await expect(
              page.getByRole("button", { name: "Toggle navigation" }),
            ).toHaveCount(
              ["/joutak", "/minigames"].includes(route.path) ? 1 : 0,
            );
            const offset = await page
              .getByTestId("header-server-selector")
              .evaluate((element) => {
                const selector = element.getBoundingClientRect();
                const header = element.closest("nav").getBoundingClientRect();
                return Math.abs(
                  selector.left +
                    selector.width / 2 -
                    header.left -
                    header.width / 2,
                );
              });
            expect(
              offset,
              `${width}px ${route.path} server selector center`,
            ).toBeLessThanOrEqual(1);
          }

          await expect
            .poll(
              () =>
                page.evaluate(() => {
                  const layoutWidth = document.documentElement.clientWidth;
                  const bodyOverflow = document.body.scrollWidth > layoutWidth;
                  const documentOverflow =
                    document.documentElement.scrollWidth > layoutWidth;
                  if (!bodyOverflow && !documentOverflow) return null;
                  return {
                    bodyWidth: document.body.scrollWidth,
                    documentWidth: document.documentElement.scrollWidth,
                    layoutWidth,
                    offenders: [...document.querySelectorAll("body *")]
                      .map((element) => {
                        const rect = element.getBoundingClientRect();
                        return {
                          tag: element.tagName,
                          className:
                            typeof element.className === "string"
                              ? element.className
                              : "",
                          left: Math.round(rect.left),
                          right: Math.round(rect.right),
                        };
                      })
                      .filter(
                        ({ left, right }) =>
                          left < -1 || right > layoutWidth + 1,
                      )
                      .slice(0, 8),
                  };
                }),
              { message: `${variant} ${width}px ${route.path} overflow` },
            )
            .toBeNull();

          await expect
            .poll(() =>
              page.evaluate(() => {
                const header = document
                  .querySelector("header")
                  .getBoundingClientRect();
                const main = document
                  .querySelector("main")
                  .getBoundingClientRect();
                return main.top - header.bottom;
              }),
            )
            .toBeGreaterThanOrEqual(-1);
        });
      }
    });
  }
}

test("tester v2 has no serious or critical axe findings", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("link", { name: "Основное действие" }),
  ).toBeVisible();
  const results = await new AxeBuilder({ page })
    .exclude("[data-design-placeholder='true']")
    .analyze();
  const blocking = results.violations.filter(({ impact }) =>
    ["serious", "critical"].includes(impact),
  );
  expect(blocking).toEqual([]);
});

test("initial image transfer stays within the responsive budgets", async ({
  page,
}) => {
  for (const [width, budget] of [
    [375, 1.5 * 1024 * 1024],
    [1440, 3 * 1024 * 1024],
  ]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(
      page.getByRole("link", { name: "Основное действие" }),
    ).toBeVisible();
    await page.waitForLoadState("networkidle");
    const imageBytes = await page.evaluate(() =>
      performance
        .getEntriesByType("resource")
        .filter((entry) => entry.initiatorType === "img")
        .reduce(
          (total, entry) =>
            total + (entry.transferSize || entry.decodedBodySize),
          0,
        ),
    );
    expect(imageBytes).toBeLessThanOrEqual(budget);
  }
});

for (const width of [320, 768, 1440]) {
  test(`system pages stay usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.route("https://forms.yandex.ru/**", (route) =>
      route.fulfill({
        contentType: "text/html",
        body: "<!doctype html><title>Payment test fixture</title><p>Payment form</p>",
      }),
    );
    for (const [path, title] of [
      ["/joutak/pay", "Оплата доступа"],
      ["/session-expired", "Сессия завершена"],
      ["/reset-password", "Сброс пароля"],
      ["/confirm-email", "Подтверждение email"],
      ["/privacy-policy", "Политика конфиденциальности"],
      ["/terms-of-use", "Условия использования"],
      ["/missing", "Такой страницы нет"],
    ]) {
      await page.goto(path);
      await expect(
        page.getByRole("heading", { level: 1, name: title, exact: true }),
      ).toBeVisible();
      expect(
        await page.evaluate(
          () =>
            document.documentElement.scrollWidth <=
            document.documentElement.clientWidth,
        ),
      ).toBe(true);
      if (path === "/joutak/pay") {
        await expect(
          page.getByRole("link", { name: "Открыть форму отдельно" }),
        ).toHaveAttribute(
          "href",
          "https://forms.yandex.ru/u/6515e3dcd04688fca3cc271b",
        );
        expect(
          await page
            .locator("iframe.pay")
            .evaluate((frame) => frame.clientHeight),
        ).toBeGreaterThanOrEqual(1500);
      }
    }
  });
}

for (const width of [320, 390, 768, 1024, 1440, 2560]) {
  test(`v2 navigation and Cyrillic typography fit at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/minigames");
    const title = page.getByRole("heading", { name: "Играть и участвовать" });
    await expect(title).toBeVisible();
    await page.evaluate(() => document.fonts.ready);

    const header = page.locator("header").first();
    const bounds = await header.boundingBox();
    const controls = await header.locator("button").evaluateAll((buttons) =>
      buttons
        .filter(
          (button) =>
            !button.closest('[aria-hidden="true"]') &&
            button.getClientRects().length,
        )
        .map((button) => {
          const rect = button.getBoundingClientRect();
          return {
            label: button.textContent || button.getAttribute("aria-label"),
            top: rect.top,
            bottom: rect.bottom,
          };
        }),
    );
    for (const control of controls) {
      expect(control.top, control.label).toBeGreaterThanOrEqual(bounds.y);
      expect(control.bottom, control.label).toBeLessThanOrEqual(
        bounds.y + bounds.height,
      );
    }
    if (width > 1024) {
      const logo = await header
        .getByRole("img", { name: "Logo", exact: true })
        .boundingBox();
      expect(
        Math.abs(logo.x + logo.width / 2 - (bounds.x + bounds.width / 2)),
      ).toBeLessThan(20);
    }

    const typography = await title.evaluate((element) => {
      const style = getComputedStyle(element);
      const context = document.createElement("canvas").getContext("2d");
      context.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
      const metrics = context.measureText(element.textContent);
      return {
        lineHeight: parseFloat(style.lineHeight),
        inkHeight:
          metrics.actualBoundingBoxAscent + metrics.actualBoundingBoxDescent,
      };
    });
    expect(typography.lineHeight).toBeGreaterThan(typography.inkHeight + 4);
    const section = page.getByRole("region", { name: "Играть и участвовать" });
    const sectionBounds = await section.boundingBox();
    for (const link of await section.getByRole("link").all()) {
      const rect = await link.boundingBox();
      expect(rect.x).toBeGreaterThanOrEqual(sectionBounds.x);
      expect(rect.x + rect.width).toBeLessThanOrEqual(
        sectionBounds.x + sectionBounds.width,
      );
      expect(
        await link.evaluate(
          (element) => element.scrollWidth <= element.clientWidth,
        ),
      ).toBe(true);
    }
  });
}

for (const width of [320, 768, 1440, 2560]) {
  test(`gallery frames and controls stay above the footer at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/joutak");
    const tabs = page.getByRole("group", { name: "Разделы галереи" });
    await expect(tabs).toBeVisible();
    const gallery = tabs.locator("..");
    await gallery.scrollIntoViewIfNeeded();
    await expect(gallery.getByText("Скриншот готовится")).toBeVisible();
    for (const state of ["placeholder", "photo"]) {
      if (state === "photo") {
        await gallery.getByRole("button", { name: "Next photo" }).click();
        await expect(gallery.getByText("2/2")).toBeVisible();
        await expect(
          gallery.getByRole("img", { name: "JouTak gallery" }),
        ).toBeVisible();
      }
      const bounds = await gallery.boundingBox();
      const children = await gallery
        .locator("img, button, [role='status']")
        .evaluateAll((elements) =>
          elements.map((element) => {
            const rect = element.getBoundingClientRect();
            return {
              left: rect.left,
              right: rect.right,
              top: rect.top,
              bottom: rect.bottom,
            };
          }),
        );
      for (const rect of children) {
        expect(rect.left).toBeGreaterThanOrEqual(bounds.x);
        expect(rect.right).toBeLessThanOrEqual(bounds.x + bounds.width + 1);
        expect(rect.top).toBeGreaterThanOrEqual(bounds.y);
        expect(rect.bottom).toBeLessThanOrEqual(bounds.y + bounds.height + 1);
      }
      const footer = await page.getByRole("contentinfo").boundingBox();
      expect(bounds.y + bounds.height).toBeLessThanOrEqual(footer.y);
    }
  });
}

test("pending page data has an accessible loading state", async ({ page }) => {
  let release;
  const pending = new Promise((resolve) => {
    release = resolve;
  });
  await page.route("http://127.0.0.1:8000/bff/pages/**", async (route) => {
    await pending;
    await route.fallback();
  });
  try {
    await page.goto("/");
    await expect(
      page.getByRole("status", { name: "" }).filter({ hasText: "Загрузка..." }),
    ).toBeVisible();
    const results = await new AxeBuilder({ page })
      .include('[role="status"]')
      .analyze();
    expect(
      results.violations.filter(({ impact }) =>
        ["serious", "critical"].includes(impact),
      ),
    ).toEqual([]);
  } finally {
    release();
  }
  await expect(
    page.getByRole("link", { name: "Основное действие" }),
  ).toBeVisible();
});

for (const theme of ["light", "dark"]) {
  for (const width of [320, 1440]) {
    test(`theme readability ${theme} at ${width}px`, async ({
      page,
    }, testInfo) => {
      test.setTimeout(120_000);
      await page.addInitScript(
        (value) => localStorage.setItem("joutak_theme_v1", value),
        theme,
      );
      await page.setViewportSize({ width, height: 1000 });
      await page.route("https://forms.yandex.ru/**", (route) =>
        route.fulfill({
          contentType: "text/html",
          body: "<!doctype html><title>Payment fixture</title><p>Payment form</p>",
        }),
      );
      for (const path of [
        "/",
        "/joutak",
        "/joutak/pay",
        "/itmocraft",
        "/legacy",
        "/minigames",
        "/contact",
        "/privacy-policy",
        "/session-expired",
        "/confirm-email",
        "/reset-password",
        "/terms-of-use",
        "/missing",
        "/login",
      ]) {
        await page.goto(path, { waitUntil: "networkidle" });
        await page.evaluate(() => document.fonts.ready);
        expect(
          await page.evaluate(
            () =>
              document.documentElement.scrollWidth <=
              document.documentElement.clientWidth,
          ),
        ).toBe(true);
        const { violations } = await new AxeBuilder({ page })
          .withRules(["color-contrast"])
          .analyze();
        expect(violations, `${theme} ${width}px ${path}`).toEqual([]);
        if (["/joutak", "/contact", "/privacy-policy"].includes(path)) {
          await page.screenshot({
            path: testInfo.outputPath(`${theme}-${path.slice(1)}.png`),
            fullPage: true,
          });
        }
      }
    });
  }
}

for (const theme of ["light", "dark"]) {
  test(`account forms readable in ${theme}`, async ({ page }) => {
    test.setTimeout(60_000);
    await page.setViewportSize({ width: 320, height: 1000 });
    await page.addInitScript((value) => {
      localStorage.setItem("joutak_theme_v1", value);
      sessionStorage.setItem(
        "joutak_auth",
        JSON.stringify({ session_token: "visual-fixture" }),
      );
    }, theme);
    let accountComplete = true;
    await page.route("http://127.0.0.1:8000/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.startsWith("/bff/")) return route.fallback();
      let body = { data: [] };
      if (path.endsWith("/auth/me"))
        body = {
          username: "design-tester",
          email: "tester@example.com",
          email_verified: true,
          profile_state: accountComplete ? "personalized" : "basic",
          profile_complete: accountComplete,
          registration_completed: accountComplete,
          personalization_interstitial_enabled: false,
          personalization_ui_enabled: true,
          personalization_context: "new_registration",
          missing_fields: ["minecraft_nick", "vk_username"],
          has_2fa: false,
        };
      if (path.endsWith("/account/sessions")) body = [];
      if (path.endsWith("/account/email"))
        body = {
          data: [
            { email: "tester@example.com", primary: true, verified: true },
          ],
        };
      if (path.endsWith("/authenticators/totp"))
        body = { data: { enabled: false } };
      await route.fulfill({
        status: route.request().method() === "OPTIONS" ? 204 : 200,
        headers: {
          "access-control-allow-origin": "http://127.0.0.1:4173",
          "access-control-allow-credentials": "true",
          "access-control-allow-headers": "*",
        },
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    });
    for (const [path, title] of [
      ["/account/security", "Настройки и безопасность"],
      ["/account/complete-registration", "Заверши регистрацию"],
    ]) {
      accountComplete = path === "/account/security";
      await page.goto(path, { waitUntil: "networkidle" });
      await expect(
        page.getByRole("heading", { name: title, exact: true }),
      ).toBeVisible();
      expect(
        await page.evaluate(
          () =>
            document.documentElement.scrollWidth <=
            document.documentElement.clientWidth,
        ),
      ).toBe(true);
      const { violations } = await new AxeBuilder({ page })
        .withRules(["color-contrast"])
        .analyze();
      expect(violations).toEqual([]);
    }
  });
}

for (const theme of ["light", "dark"]) {
  test(`legacy login dialog centered in ${theme}`, async ({
    page,
  }, testInfo) => {
    await page.unroute("http://127.0.0.1:8000/bff/pages/**");
    await mockPageDocuments(page, { variant: "legacy" });
    await page.addInitScript(
      (value) => localStorage.setItem("joutak_theme_v1", value),
      theme,
    );
    await page.setViewportSize({ width: 375, height: 900 });
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute(
      "data-site-design",
      "legacy",
    );
    await page.getByRole("button", { name: "Войти", exact: true }).click();
    const dialog = page.getByRole("dialog");
    await expect(
      dialog.getByRole("textbox", { name: "Email", exact: true }),
    ).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    const bounds = await dialog.evaluate((element) => {
      const box = element.getBoundingClientRect();
      return {
        left: box.left,
        right: document.documentElement.clientWidth - box.right,
        overflow: element.scrollWidth > element.clientWidth,
      };
    });
    expect(bounds.left).toBeGreaterThanOrEqual(15);
    expect(Math.abs(bounds.left - bounds.right)).toBeLessThanOrEqual(2);
    expect(bounds.overflow).toBe(false);
    const { violations } = await new AxeBuilder({ page })
      .withRules(["color-contrast"])
      .analyze();
    expect(violations).toEqual([]);
    await page.screenshot({
      path: testInfo.outputPath(`legacy-login-${theme}.png`),
    });
  });
}

for (const theme of ["light", "dark"]) {
  test(`V2 notification and legacy header remain readable in ${theme}`, async ({
    page,
  }, testInfo) => {
    await page.addInitScript(
      (value) => localStorage.setItem("joutak_theme_v1", value),
      theme,
    );
    await page.goto("/");
    const title = page.getByText("Комьюнити", { exact: true });
    await expect(title).toBeVisible();
    await expect(title).toHaveCSS("color", "rgb(23, 19, 10)");
    await expect(title).toHaveCSS("text-shadow", "none");
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: testInfo.outputPath(`v2-${theme}.png`) });
    await page.getByRole("button", { name: "Открыть список серверов" }).click();
    await page.getByRole("button", { name: "Legacy", exact: true }).click();
    await expect(page).toHaveURL(/\/legacy$/);
    await expect(page.locator("html")).toHaveAttribute(
      "data-site-design",
      "legacy",
    );
    const { violations } = await new AxeBuilder({ page })
      .include("header")
      .withRules(["color-contrast"])
      .analyze();
    expect(violations).toEqual([]);
  });
}
