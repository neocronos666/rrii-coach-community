import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

for (const route of ["assets", "products", "quick-quotes", "test-prints"]) {
  test(`navegación táctil y teclado: ${route} 768px`, async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 960 });
    expect(await page.evaluate(() => navigator.maxTouchPoints)).toBeGreaterThan(
      0,
    );
    for (const mode of ["light", "dark"]) {
      await page.addInitScript(
        (value) => localStorage.setItem("rrii-coach.appearance.v1", value),
        mode,
      );
      await page.goto(`/${route}`);
      await expect(page.locator("main h1")).toBeVisible();
      await page.waitForLoadState("networkidle");
      await expect(page.locator("html")).toHaveClass(new RegExp(mode));
      expect(
        JSON.parse(
          (await page.evaluate(() =>
            localStorage.getItem("rrii-coach.device.v1"),
          )) || "{}",
        ).profile,
      ).toBe("touch");
      expect(
        (
          await new AxeBuilder({ page })
            .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
            .analyze()
        ).violations,
      ).toEqual([]);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      const link = page.locator('main a[href^="/"]').first();
      await expect(link).toBeVisible();
      const href = await link.getAttribute("href");
      const target = new URL(href!, page.url()).href;
      await link.focus();
      await expect(link).toBeFocused();
      await page.keyboard.press("Tab");
      await page.keyboard.press("Shift+Tab");
      await expect(link).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(page).toHaveURL(target);
      await page.goto(`/${route}`);
      await link.tap();
      await expect(page).toHaveURL(target);
    }
  });
}
