import AxeBuilder from "@axe-core/playwright";
import { test, expect } from "@playwright/test";
const api = process.env.RRII_E2E_API_BASE!;
test("cálculo visual, composición múltiple, edición y snapshot conservado", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  await page.setViewportSize({ width: 360, height: 960 });
  await page.goto("/calculations/new");
  await page
    .getByRole("button", { name: "Agregar extra", exact: true })
    .click();
  await page
    .getByLabel("Descripción del extra", { exact: true })
    .fill("Preparación");
  await page.getByLabel("Importe del extra", { exact: true }).fill("100.87");
  await page.getByLabel("Confirmo la creación del snapshot técnico.").check();
  await page
    .getByRole("button", { name: "Guardar cálculo técnico", exact: true })
    .click();
  const link = page.getByRole("link", { name: "Abrir snapshot permanente" });
  await expect(link).toBeVisible();
  const id = (await link.getAttribute("href"))!.split("/").at(-1)!;
  const original = await (
    await request.get(`${api}/cost-calculations/${id}`)
  ).json();
  await page.goto("/quotes/new");
  await page.getByLabel("Identificador del cálculo", { exact: true }).fill(id);
  await page
    .getByRole("button", { name: "Consultar cálculo", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Agregar cálculo a los ítems", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Agregar cálculo a los ítems", exact: true })
    .click();
  await page
    .getByLabel("Título del presupuesto", { exact: true })
    .fill(`Composición ${Date.now()}`);
  await page
    .getByLabel("Descripción del ítem", { exact: true })
    .nth(0)
    .fill("Primero");
  await page
    .getByLabel("Descripción del ítem", { exact: true })
    .nth(1)
    .fill("Segundo");
  await page
    .getByLabel("Cantidad comercial", { exact: true })
    .nth(0)
    .fill("1.000001");
  await page
    .getByLabel("Cantidad comercial", { exact: true })
    .nth(1)
    .fill("2.123456");
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByLabel("Confirmo los ítems y sus cantidades.").check();
  await page
    .getByRole("button", { name: "Crear presupuesto", exact: true })
    .click();
  await expect(page).toHaveURL(/\/quotes\/[0-9a-f-]{36}$/);
  const quoteId = page.url().split("/").at(-1);
  const quote = await (await request.get(`${api}/quotes/${quoteId}`)).json();
  expect(quote.items.map((row: { quantity: string }) => row.quantity)).toEqual([
    "1.000001",
    "2.123456",
  ]);
  await page.getByRole("link", { name: "Editar ítems técnicos" }).click();
  await page.getByRole("button", { name: "Quitar ítem 2" }).click();
  await page.getByLabel("Confirmo los ítems y sus cantidades.").check();
  await page
    .getByRole("button", { name: "Guardar composición", exact: true })
    .click();
  await expect(page).toHaveURL(`/quotes/${quoteId}`);
  expect(
    (await (await request.get(`${api}/quotes/${quoteId}`)).json()).items,
  ).toHaveLength(1);
  expect(
    await (await request.get(`${api}/cost-calculations/${id}`)).json(),
  ).toEqual(original);
});
test("creación con respuesta perdida se revisa sin duplicar", async ({
  page,
  request,
}) => {
  const calc = await (
    await request.post(`${api}/cost-calculations`, {
      data: {
        extras: [{ description: "Extra", amount: "10", currency: "ARS" }],
      },
    })
  ).json();
  const title = `Incierto ${Date.now()}`;
  await page.goto("/quotes/new");
  await page
    .getByLabel("Identificador del cálculo", { exact: true })
    .fill(calc.id);
  await page
    .getByRole("button", { name: "Consultar cálculo", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Agregar cálculo a los ítems", exact: true })
    .click();
  await page.getByLabel("Título del presupuesto", { exact: true }).fill(title);
  await page.getByLabel("Descripción del ítem", { exact: true }).fill("Pieza");
  await page.getByLabel("Confirmo los ítems y sus cantidades.").check();
  let posts = 0;
  await page.route("**/api/v1/quotes", async (route) => {
    if (route.request().method() === "POST") {
      posts++;
      await route.fetch();
      await route.abort("failed");
    } else await route.continue();
  });
  await page
    .getByRole("button", { name: "Crear presupuesto", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "Revisar operación incierta" }),
  ).toBeVisible();
  page.on("dialog", (dialog) => dialog.accept());
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Crear presupuesto", exact: true }),
  ).toBeDisabled();
  expect(posts).toBe(1);
  expect(
    (await (await request.get(`${api}/quotes`)).json()).filter(
      (row: { title: string }) => row.title === title,
    ),
  ).toHaveLength(1);
});
