import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

for (const width of [320, 768, 1440, 2560]) {
  test(`Markdown documents and version links work at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    for (const [path, title] of [
      ["/privacy-policy", "Политика конфиденциальности"],
      ["/terms-of-use", "Условия использования"],
    ]) {
      await page.goto(`${path}?version=2026-09-21`, {
        waitUntil: "domcontentloaded",
      });
      await expect(
        page.getByRole("heading", { level: 1, name: title }),
      ).toBeVisible();
      await expect(page.getByRole("table")).toBeVisible();
      await page.evaluate(() => document.fonts.ready);
      expect(
        await page.evaluate(
          () =>
            document.documentElement.scrollWidth <=
            document.documentElement.clientWidth,
        ),
      ).toBe(true);
      await expect(page.getByText(/макет|демонстрационный текст/i)).toHaveCount(
        0,
      );
      const toc = page.getByRole("navigation", {
        name: "Содержание документа",
      });
      const sectionLink = toc.getByRole("link").last();
      const target = await sectionLink.getAttribute("href");
      await sectionLink.click();
      expect(decodeURIComponent(new URL(page.url()).hash)).toBe(target);
      await expect(page.locator(target)).toBeInViewport();
      await page.reload({ waitUntil: "domcontentloaded" });
      await expect(page.locator(target)).toBeInViewport();
      await page.goto(`${path}?version=missing&from=footer`, {
        waitUntil: "domcontentloaded",
      });
      await expect(page.getByRole("status")).toContainText(
        "Такая редакция документа не найдена",
      );
      await page
        .getByRole("button", { name: "Открыть текущую редакцию" })
        .click();
      await expect(page).toHaveURL(/version=2026-09-21&from=footer/);
      await expect(page.getByRole("table")).toBeVisible();
    }
  });
}

for (const theme of ["dark", "light"]) {
  test(`Markdown document content is accessible in ${theme} theme`, async ({
    page,
  }) => {
    await page.addInitScript(
      (value) => localStorage.setItem("joutak_theme_v1", value),
      theme,
    );
    await page.goto("/privacy-policy", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("table")).toBeVisible();
    // Check this document surface independently of the unchanged legacy footer.
    const { violations } = await new AxeBuilder({ page })
      .include("main")
      .analyze();
    expect(
      violations.filter(({ impact }) =>
        ["serious", "critical"].includes(impact),
      ),
    ).toEqual([]);
  });
}
