import { expect, test } from "@playwright/test";
test("personaliza bloques, conserva preferencias y recupera un dashboard vacío", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Personalizar dashboard", exact: true })
    .click();
  const machines = page.getByRole("group", { name: "Máquinas", exact: true });
  await machines.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Subir Máquinas" }).click();
  await page
    .getByLabel("Vista de Producción", { exact: true })
    .selectOption("summary");
  await page
    .getByLabel("Tamaño de Producción", { exact: true })
    .selectOption("wide");
  await page.getByRole("button", { name: "Listo", exact: true }).click();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Máquinas", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () =>
        JSON.parse(
          localStorage.getItem("rrii-coach.dashboard.v1")!,
        ).blocks.find((row: { id: string }) => row.id === "production").view,
    ),
  ).toBe("summary");
  await expect(page.locator('[data-block="production"]')).toHaveClass(
    /block-wide/,
  );
  await page
    .getByRole("button", { name: "Opciones de Producción", exact: true })
    .click();
  await page.getByRole("menuitem", { name: "Ocultar", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Producción", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Personalizar dashboard", exact: true }),
  ).toBeFocused();
  await page
    .getByRole("button", { name: "Personalizar dashboard", exact: true })
    .click();
  for (const checkbox of await page
    .getByRole("dialog")
    .getByRole("checkbox")
    .all())
    await checkbox.uncheck();
  await page.getByRole("button", { name: "Listo", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Un espacio a tu medida" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Elegir bloques", exact: true })
    .click();
  await page.getByRole("button", { name: "Restablecer distribución" }).click();
  await page.getByRole("button", { name: "Listo", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Producción", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Máquinas", exact: true }),
  ).toHaveCount(0);
});

test("el menú contextual mueve entre bloques visibles", async ({ page }) => {
  await page.goto("/");
  await page
    .getByRole("button", {
      name: "Opciones de Actividad reciente",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("menuitem", { name: "Bajar", exact: true }),
  ).toBeDisabled();
  await page.keyboard.press("Escape");
  await page
    .getByRole("button", { name: "Opciones de Presupuestos", exact: true })
    .click();
  await page.getByRole("menuitem", { name: "Ocultar", exact: true }).click();
  await page
    .getByRole("button", { name: "Opciones de Producción", exact: true })
    .click();
  await page.getByRole("menuitem", { name: "Bajar", exact: true }).click();
  await expect(page.locator("[data-block]").first()).toHaveAttribute(
    "data-block",
    "attention",
  );
  await page.reload();
  await expect(page.locator("[data-block]").first()).toHaveAttribute(
    "data-block",
    "attention",
  );
});
