import { expect, test } from "@playwright/test";
test("personaliza, reordena y recupera launcher en otras rutas", async ({
  page,
}) => {
  await page.goto("/");
  const open = async () => {
    await page.getByRole("button", { name: "Crear", exact: true }).click();
  };
  await open();
  await page
    .getByRole("menuitem", { name: "Personalizar…", exact: true })
    .click();
  await page.getByRole("button", { name: "Subir Cotizar pedido" }).click();
  await page.getByLabel("Presupuesto rápido", { exact: true }).uncheck();
  await page.keyboard.press("Escape");
  await page.goto("/products");
  await open();
  await expect(page.getByRole("menuitem").first()).toContainText(
    "Cotizar pedido",
  );
  await expect(
    page.getByRole("menuitem", { name: /Presupuesto rápido/ }),
  ).toHaveCount(0);
  await page.getByRole("menuitem", { name: /Cotizar pedido/ }).click();
  await expect(page).toHaveURL("/quotes/new");
  await expect(
    page.getByRole("heading", {
      name: "Presupuesto con ítems técnicos",
      exact: true,
    }),
  ).toBeVisible();
  await open();
  await page
    .getByRole("menuitem", { name: "Personalizar…", exact: true })
    .click();
  await page.getByLabel("Cotizar pedido", { exact: true }).uncheck();
  await page.keyboard.press("Escape");
  await open();
  await expect(
    page.getByRole("menuitem", { name: "Personalizar…", exact: true }),
  ).toBeVisible();
});
