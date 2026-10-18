import { expect, test } from "@playwright/test";
for (const width of [390, 1440]) {
  test(`shell navegable a ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    page.on("pageerror", (error) => {
      throw error;
    });
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Tu taller, en movimiento." }),
    ).toBeVisible();
    await expect(page.locator("html")).toHaveClass(/dark/);
    await page.screenshot({
      path: `test-results/shell-${width}-dark.png`,
      fullPage: true,
    });
    await page.getByRole("button", { name: "Cambiar claro / oscuro" }).click();
    await expect(page.locator("html")).toHaveClass(/light/);
    await page.screenshot({
      path: `test-results/shell-${width}-light.png`,
      fullPage: true,
    });
    await page.reload();
    await expect(page.locator("html")).toHaveClass(/light/);
    await page
      .getByRole("link", { name: "Presupuestos", exact: true })
      .filter({ visible: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Presupuestos", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Crear", exact: true }).click();
    await expect(page.getByRole("menuitem").first()).toContainText(
      "Presupuesto rápido",
    );
    await page.keyboard.press("Escape");
    await expect(
      page.getByRole("button", { name: "Crear", exact: true }),
    ).toBeFocused();
    await page
      .getByRole("button", { name: "Configuración", exact: true })
      .click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.press("Escape");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
}
