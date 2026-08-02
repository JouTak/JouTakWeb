import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const ROUTES = [
  { path: "/", product: "itmocraft", legacyAlias: false },
  { path: "/itmocraft", product: "itmocraft", legacyAlias: true },
  { path: "/joutak", product: "joutak", legacyAlias: false },
  { path: "/minigames", product: "minigames", legacyAlias: false },
];
const WIDTHS = [320, 375, 480, 768, 1024, 1440];

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
      sections: legacy
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
              title: `Действия ${product}`,
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
                  label: "Внутреннее действие",
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
                  photos: [asset("gallery.joutak.cover", "JouTak gallery")],
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

test("route and viewport matrix has no horizontal overflow or header overlap", async ({
  page,
}) => {
  for (const variant of ["legacy", "v2"]) {
    await page.unroute("http://127.0.0.1:8000/bff/pages/**");
    await mockPageDocuments(page, { variant });

    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: 900 });
      for (const route of ROUTES) {
        await test.step(`${variant} ${width}px ${route.path}`, async () => {
          await page.goto(route.path);
          await expect(page.locator("main")).toBeVisible();
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
    }
  }
});

test("tester v2 has no serious or critical axe findings", async ({ page }) => {
  await page.goto("/");
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
