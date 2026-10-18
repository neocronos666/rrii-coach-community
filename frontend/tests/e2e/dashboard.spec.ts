import { expect, test } from "@playwright/test";
const api = process.env.RRII_E2E_API_BASE!;
test("dashboard usa registros reales y navega al presupuesto", async ({
  page,
  request,
}) => {
  const calculation = await (
    await request.post(`${api}/cost-calculations`, {
      data: {
        extras: [
          { description: "Dashboard", amount: "10.87", currency: "ARS" },
        ],
      },
    })
  ).json();
  const quote = await (
    await request.post(`${api}/quotes`, {
      data: {
        title: `Dashboard ${Date.now()}`,
        items: [
          {
            cost_calculation_id: calculation.id,
            description: "Registro real",
            quantity: "1",
          },
        ],
      },
    })
  ).json();
  // El listado puede tener muchas fixtures previas: la API devuelve el registro creado.
  await page.route("**/api/v1/quotes", async (route) => {
    const response = await route.fetch();
    const rows = await response.json();
    await route.fulfill({
      response,
      json: rows.filter((row: { id: string }) => row.id === quote.id),
    });
  });
  await page.goto("/");
  await expect(
    page.getByText("Vista de demostración", { exact: true }),
  ).toHaveCount(0);
  const block = page.locator('[data-block="quotes"]');
  await expect(block).toContainText(quote.title);
  await expect(block).toContainText(
    `${quote.currency} ${quote.breakdown.final_price}`,
  );
  await block
    .getByRole("link", { name: `${quote.code} · ${quote.title}`, exact: true })
    .click();
  await expect(page).toHaveURL(`/quotes/${quote.id}`);
});
test("vacíos y caída de un bloque no inventan métricas", async ({ page }) => {
  await page.route("**/api/v1/production-tasks*", (route) =>
    route.fulfill({
      status: 503,
      json: { detail: "Producción temporalmente no disponible" },
    }),
  );
  await page.route("**/api/v1/quotes", (route) => route.fulfill({ json: [] }));
  await page.goto("/");
  const production = page.locator('[data-block="production"]'),
    quotes = page.locator('[data-block="quotes"]');
  await expect(production.getByRole("alert")).toContainText(
    "No se pudo actualizar",
  );
  await expect(production.getByTestId("dashboard-count")).toHaveCount(0);
  await expect(quotes.getByTestId("dashboard-count")).toHaveText("0 registros");
  await page.unroute("**/api/v1/production-tasks*");
  await page.route("**/api/v1/production-tasks*", (route) =>
    route.fulfill({ json: [] }),
  );
  await production.getByRole("button", { name: "Actualizar bloque" }).click();
  await expect(production.getByTestId("dashboard-count")).toHaveText(
    "0 registros",
  );
});
test("búsqueda de secciones y enlace Insumos llegan a pantallas operativas", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.goto("/");
  await page
    .getByRole("searchbox", { name: "Buscar sección", exact: true })
    .fill("categorias");
  await page
    .locator(".section-search-results")
    .getByRole("link", { name: "Categorías de Assets" })
    .click();
  await expect(page).toHaveURL("/asset-categories");
  await page
    .getByRole("searchbox", { name: "Buscar sección", exact: true })
    .fill("insumos");
  await page
    .getByRole("navigation", { name: "Resultados de secciones" })
    .getByRole("link", { name: "Insumos", exact: true })
    .click();
  await expect(page).toHaveURL("/inventory");
  await page.goto("/supplies");
  await expect(page).toHaveURL("/inventory");
  await page.goto("/no-existe");
  await expect(
    page.getByText("Página no encontrada", { exact: true }).first(),
  ).toBeVisible();
});
