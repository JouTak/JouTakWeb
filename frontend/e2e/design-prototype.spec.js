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
                eyebrow: "Design prototype",
                title: product,
                description: "Tester-only page",
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

          const header = await page.locator("header").boundingBox();
          const main = await page.locator("main").boundingBox();
          expect(header).not.toBeNull();
          expect(main).not.toBeNull();
          expect(main.y).toBeGreaterThanOrEqual(header.y + header.height - 1);
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
