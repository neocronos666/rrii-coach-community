import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
for (const width of [320, 360, 768, 1440])
  for (const mode of ["dark", "light"]) {
    test(`accesibilidad ${mode} ${width}px`, async ({ page }) => {
      const errors: string[] = [];
      page.on("pageerror", (error) => errors.push(error.message));
      await page.setViewportSize({ width, height: 960 });
      await page.addInitScript(
        ({ mode, width }) => {
          localStorage.setItem("rrii-coach.appearance.v1", mode);
          localStorage.setItem(
            "rrii-coach.device.v1",
            JSON.stringify({
              version: 1,
              profile: width === 768 ? "touch" : "auto",
              density: "comfortable",
            }),
          );
        },
        { mode, width },
      );
      await page.goto("/");
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await page.waitForLoadState("networkidle");
      await expect(page.locator("html")).toHaveClass(new RegExp(mode));
      const result = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();
      expect(result.violations).toEqual([]);
      const smallTargets = await page
        .locator("button, a")
        .evaluateAll((elements) =>
          elements
            .filter((element) => {
              const box = element.getBoundingClientRect();
              const style = getComputedStyle(element);
              if (
                box.width === 0 ||
                box.height === 0 ||
                box.bottom < 0 ||
                style.visibility === "hidden"
              )
                return false;
              return box.width < 44 || box.height < 44;
            })
            .map(
              (element) =>
                element.getAttribute("aria-label") || element.textContent,
            ),
        );
      expect(smallTargets).toEqual([]);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      await page.screenshot({
        path: `test-results/nebula-${mode}-${width}.png`,
        fullPage: true,
      });
      await page
        .getByRole("button", { name: "Personalizar dashboard", exact: true })
        .click();
      await expect(page.getByRole("dialog")).toBeVisible();
      const panel = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();
      expect(panel.violations).toEqual([]);
      await page.keyboard.press("Escape");
      await expect(
        page.getByRole("button", {
          name: "Personalizar dashboard",
          exact: true,
        }),
      ).toBeFocused();
      expect(errors).toEqual([]);
    });
  }
test("teclado, sidebar contraída y movimiento reducido", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Saltar al contenido" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
  await page
    .getByRole("button", { name: "Contraer navegación", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Expandir navegación", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Productos", exact: true })
    .filter({ visible: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Productos", exact: true }),
  ).toBeVisible();
  await expect(page.locator("#main-content")).toBeFocused();
  expect(
    await page
      .getByRole("button", { name: "Crear", exact: true })
      .evaluate((element) => getComputedStyle(element).transitionDuration),
  ).toBe("0s");
});
test("abre con preferencias corruptas y sin servicios externos", async ({
  page,
}) => {
  await page.addInitScript(() => {
    for (const key of ["device", "launcher", "dashboard"])
      localStorage.setItem(`rrii-coach.${key}.v1`, "{broken");
    localStorage.setItem("rrii-coach.appearance.v1", "invalid");
  });
  const external: string[] = [];
  await page.route("**/*", (route) => {
    const url = new URL(route.request().url());
    const apiHost = process.env.RRII_E2E_API_BASE
      ? new URL(process.env.RRII_E2E_API_BASE).hostname
      : "localhost";
    if (!["127.0.0.1", "localhost", apiHost].includes(url.hostname)) {
      external.push(url.hostname);
      return route.abort();
    }
    return route.continue();
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Tu taller, en movimiento." }),
  ).toBeVisible();
  await page.waitForLoadState("networkidle");
  await expect(page.locator("html")).toHaveClass(/dark/);
  await expect(
    page.getByRole("heading", { name: "Producción", exact: true }),
  ).toBeVisible();
  const missingIcons = await page
    .locator(".iconify")
    .evaluateAll(
      (elements) =>
        elements.filter(
          (element) => getComputedStyle(element).maskImage === "none",
        ).length,
    );
  expect(missingIcons).toBe(0);
  expect(external).toEqual([]);
});
