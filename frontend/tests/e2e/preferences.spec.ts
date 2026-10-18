import { expect, test } from "@playwright/test";
test("fuerza perfiles y conserva preferencias del dispositivo", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Configuración", exact: true })
    .click();
  await page.getByLabel("Perfil de pantalla").selectOption("mobile");
  await page.getByLabel("Densidad", { exact: true }).selectOption("compact");
  await page.keyboard.press("Escape");
  await expect(page.locator("html")).toHaveAttribute(
    "data-navigation",
    "bottom",
  );
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute(
    "data-display-profile",
    "mobile",
  );
  await page
    .getByRole("button", { name: "Configuración", exact: true })
    .click();
  await page.getByLabel("Perfil de pantalla").selectOption("touch");
  await page.keyboard.press("Escape");
  await expect(page.locator("html")).toHaveAttribute(
    "data-display-profile",
    "touch",
  );
  const box = await page
    .getByRole("button", { name: "Crear", exact: true })
    .boundingBox();
  expect(box!.height).toBeGreaterThanOrEqual(52);
  await page.setViewportSize({ width: 390, height: 900 });
  await expect(page.locator("html")).toHaveAttribute(
    "data-navigation",
    "bottom",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
test("abre con almacenamiento bloqueado", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "localStorage", {
      get() {
        throw new Error("blocked");
      },
    });
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page
    .getByRole("button", { name: "Configuración", exact: true })
    .click();
  await page.getByLabel("Perfil de pantalla").selectOption("touch");
  await expect(page.getByRole("dialog").getByRole("status")).toContainText(
    "no permite guardar",
  );
});
