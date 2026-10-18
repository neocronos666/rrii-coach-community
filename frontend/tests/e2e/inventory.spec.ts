import AxeBuilder from "@axe-core/playwright";
import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
import { randomUUID } from "node:crypto";
const api = process.env.RRII_E2E_API_BASE!;
test.use({ timezoneId: "America/Argentina/Rio_Gallegos" });
async function post(request: APIRequestContext, path: string, data: unknown) {
  const response = await request.post(`${api}${path}`, { data });
  expect(response.ok(), await response.text()).toBe(true);
  return response.json();
}
async function fixture(request: APIRequestContext, project = false) {
  const suffix = Date.now();
  const supply = await post(request, "/supplies", {
    name: `Inventario ${suffix}`,
    category: "material",
    base_unit: "g",
  });
  const product = await post(request, "/products", {
    name: `Stock ${suffix}`,
    initial_variant: { name: "Variante stock", base_unit: "unit" },
  });
  const variant = (
    await (await request.get(`${api}/products/${product.id}/variants`)).json()
  )[0];
  const cost = await post(request, "/cost-calculations", {
    extras: [{ description: "Preparación", amount: "10.87", currency: "ARS" }],
  });
  const quote = await post(request, "/quotes", {
    title: `Inventario ${suffix}`,
    markup_percentage: "0",
    items: Array.from({ length: project ? 2 : 1 }, (_, index) => ({
      description: `Item ${index}`,
      quantity: "1",
      cost_calculation_id: cost.id,
    })),
  });
  await post(request, `/quotes/${quote.id}/approve`, {});
  const conversion = await post(request, `/quotes/${quote.id}/convert`, {});
  const kind = project ? "projects" : "orders";
  const destination = await (
    await request.get(`${api}/${kind}/${conversion.target_id}`)
  ).json();
  const recipe = await post(request, `/products/${product.id}/recipe`, {
    name: `Receta inventario ${suffix}`,
  });
  const response = await request.put(`${api}/recipes/${recipe.id}/plan`, {
    data: {
      steps: [
        {
          key: "final",
          title: "Tarea inventario",
          is_final_output: true,
          supply_inputs: [{ supply_id: supply.id, quantity_per_batch: "1" }],
        },
      ],
    },
  });
  expect(response.ok(), await response.text()).toBe(true);
  const parent = project
    ? `project-components/${destination.components[0].id}`
    : `orders/${destination.id}`;
  const plan = await post(request, `/${parent}/production-plans`, {
    request_id: randomUUID(),
    recipe_id: recipe.id,
    variant_id: variant.id,
    target_quantity: "1",
    reserve_supplies: false,
    allocate_output: false,
  });
  return { supply, product, variant, destination, kind, task: plan.tasks[0] };
}
async function axe(page: Page) {
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
}
async function loseOnce(page: Page, pattern: string) {
  let count = 0,
    original: unknown;
  await page.route(pattern, async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    count++;
    const body = route.request().postDataJSON();
    if (count === 1) {
      original = body;
      const response = await route.fetch();
      expect(response.ok(), await response.text()).toBe(true);
      await route.abort();
    } else {
      expect(body).toEqual(original);
      await route.continue();
    }
  });
  return () => count;
}
async function retry(page: Page) {
  await expect(
    page.getByRole("button", {
      name: "Reintentar solicitud pendiente",
      exact: true,
    }),
  ).toBeVisible();
  await page.reload();
  await page
    .getByRole("button", {
      name: "Reintentar solicitud pendiente",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("button", {
      name: "Reintentar solicitud pendiente",
      exact: true,
    }),
  ).toHaveCount(0);
}

test("Inventario: insumo, presentación, compra, ajustes y edición en móvil", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  page.on("dialog", (dialog) => dialog.accept());
  await page.setViewportSize({ width: 360, height: 960 });
  await page.goto("/inventory");
  await page
    .getByRole("link", { name: "Registrar insumo", exact: true })
    .click();
  const name = `UI insumo ${Date.now()}`;
  await page.getByLabel("Nombre", { exact: true }).fill(name);
  await page
    .getByRole("combobox", { name: "Unidad base", exact: true })
    .selectOption("g");
  await page
    .getByLabel("Confirmo los datos indicados.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar insumo", exact: true })
    .click();
  await expect(page).toHaveURL(/\/inventory\/supplies\/[0-9a-f-]{36}$/);
  const id = page.url().split("/").pop();
  await expect(
    page.getByText(
      "Costo desconocido: no hay una compra trazable disponible.",
      { exact: true },
    ),
  ).toBeVisible();
  await page
    .locator("summary")
    .filter({ hasText: /^Registrar presentación$/ })
    .click();
  const presentation = page
    .locator("details")
    .filter({
      has: page
        .locator("summary")
        .filter({ hasText: /^Registrar presentación$/ }),
    });
  await presentation
    .getByLabel("Nombre de presentación", { exact: true })
    .fill("Bolsa 1 kg");
  await presentation
    .getByLabel("Contenido de la presentación", { exact: true })
    .fill("1");
  await presentation
    .getByRole("combobox", { name: "Unidad del contenido", exact: true })
    .selectOption("kg");
  await presentation
    .getByLabel("Confirmo los datos indicados.", { exact: true })
    .check();
  await presentation
    .getByRole("button", { name: "Registrar presentación", exact: true })
    .click();
  const purchase = page.getByRole("region", {
    name: "Registrar compra",
    exact: true,
  });
  await expect(
    purchase
      .getByRole("combobox", { name: "Presentación comprada", exact: true })
      .locator("option"),
  ).toHaveCount(2);
  await purchase
    .getByRole("combobox", { name: "Presentación comprada", exact: true })
    .selectOption({ label: "Bolsa 1 kg · 1.000000 kg" });
  await purchase.getByLabel("Cantidad comprada", { exact: true }).fill("2");
  await purchase
    .getByLabel("Costo total de la compra", { exact: true })
    .fill("1500");
  await purchase
    .getByLabel("Fecha y hora local", { exact: true })
    .fill("2026-10-14T10:00");
  await purchase
    .getByLabel("Confirmo la compra y su ingreso al stock.", { exact: true })
    .check();
  await purchase
    .getByRole("button", { name: "Registrar compra", exact: true })
    .click();
  await expect(page.getByTestId("physical")).toHaveText("2000.000000 g");
  await expect(page.getByTestId("supply-cost")).toHaveText(
    /^ARS 0\.750* \/ g$/,
  );
  const purchases = await (
    await request.get(`${api}/supplies/${id}/purchases`)
  ).json();
  expect(purchases).toHaveLength(1);
  expect(purchases[0].quantity).toBe("2000.000000");
  expect(new Date(purchases[0].purchased_at).toISOString()).toBe(
    "2026-10-14T13:00:00.000Z",
  );
  await page
    .locator("summary")
    .filter({ hasText: /^Ajustes de stock$/ })
    .click();
  const adjustment = page
    .locator("details")
    .filter({
      has: page.locator("summary").filter({ hasText: /^Ajustes de stock$/ }),
    });
  await adjustment
    .getByRole("combobox", { name: "Dirección", exact: true })
    .selectOption("out");
  await adjustment.getByLabel("Cantidad · g", { exact: true }).fill("3000");
  await adjustment.getByLabel("Motivo", { exact: true }).fill("Conteo físico");
  await adjustment
    .getByLabel("Confirmo el ajuste de existencias indicado.", { exact: true })
    .check();
  await adjustment
    .getByRole("button", { name: "Registrar ajuste", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("insuficiente");
  await expect(
    adjustment.getByLabel("Cantidad · g", { exact: true }),
  ).toHaveValue("3000");
  await adjustment.getByLabel("Cantidad · g", { exact: true }).fill("250");
  await adjustment
    .getByRole("button", { name: "Registrar ajuste", exact: true })
    .click();
  await expect(page.getByTestId("physical")).toHaveText("1750.000000 g");
  await page
    .locator("summary")
    .filter({ hasText: /^Editar insumo$/ })
    .click();
  const editor = page
    .locator("details")
    .filter({
      has: page.locator("summary").filter({ hasText: /^Editar insumo$/ }),
    });
  await editor
    .getByRole("combobox", { name: "Unidad base", exact: true })
    .selectOption("kg");
  await editor
    .getByLabel("Confirmo los datos indicados.", { exact: true })
    .check();
  await editor
    .getByRole("button", { name: "Guardar insumo", exact: true })
    .click();
  await expect(editor.getByRole("alert")).toContainText(
    "unidad base está fijada",
  );
  await editor
    .getByRole("combobox", { name: "Unidad base", exact: true })
    .selectOption("g");
  for (const title of [name + " editado", name]) {
    await editor.getByLabel("Nombre", { exact: true }).fill(title);
    await editor
      .getByLabel("Confirmo los datos indicados.", { exact: true })
      .check();
    await editor
      .getByRole("button", { name: "Guardar insumo", exact: true })
      .click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(title);
  }
  await axe(page);
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({ path: "test-results/inventory-supply-360.png" });
});

test("Inventario: compra y ajuste inciertos no se reenvían después de recargar", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  page.on("dialog", (dialog) => dialog.accept());
  const supply = await post(request, "/supplies", {
    name: `Compra incierta ${Date.now()}`,
    category: "material",
    base_unit: "g",
  });
  const purchases = await loseOnce(
    page,
    `**/api/v1/supplies/${supply.id}/purchases`,
  );
  await page.goto(`/inventory/supplies/${supply.id}`);
  const form = page.getByRole("region", {
    name: "Registrar compra",
    exact: true,
  });
  await form.getByLabel("Cantidad comprada", { exact: true }).fill("10");
  await form
    .getByLabel("Costo total de la compra", { exact: true })
    .fill("100.87");
  await form
    .getByLabel("Confirmo la compra y su ingreso al stock.", { exact: true })
    .check();
  await form
    .getByRole("button", { name: "Registrar compra", exact: true })
    .click();
  const review = page.getByRole("region", {
    name: "Revisar operación incierta",
    exact: true,
  });
  await expect(review).toBeVisible();
  await page.reload();
  await expect(review).toBeVisible();
  await expect(page.getByTestId("purchase-row")).toHaveCount(1);
  await expect(
    form.getByRole("button", { name: "Registrar compra", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", {
      name: "Reintentar solicitud pendiente",
      exact: true,
    }),
  ).toHaveCount(0);
  await review
    .getByRole("button", { name: "Consultar registros actuales", exact: true })
    .click();
  await review
    .getByLabel("Ya revisé los registros y el resultado de la operación.", {
      exact: true,
    })
    .check();
  await review
    .getByRole("button", { name: "Habilitar nueva operación", exact: true })
    .click();
  await expect(review).toHaveCount(0);
  expect(purchases()).toBe(1);
  const adjustments = await loseOnce(
    page,
    `**/api/v1/supplies/${supply.id}/adjustments`,
  );
  await page
    .locator("summary")
    .filter({ hasText: /^Ajustes de stock$/ })
    .click();
  const adjustment = page
    .locator("details")
    .filter({
      has: page.locator("summary").filter({ hasText: /^Ajustes de stock$/ }),
    });
  await adjustment.getByLabel("Cantidad · g", { exact: true }).fill("1");
  await adjustment
    .getByLabel("Motivo", { exact: true })
    .fill("Diferencia de conteo");
  await adjustment
    .getByLabel("Confirmo el ajuste de existencias indicado.", { exact: true })
    .check();
  await adjustment
    .getByRole("button", { name: "Registrar ajuste", exact: true })
    .click();
  await expect(review).toBeVisible();
  await page.reload();
  await expect(review).toBeVisible();
  await expect(page.getByTestId("physical")).toHaveText("11.000000 g");
  expect(adjustments()).toBe(1);
  expect(
    await (await request.get(`${api}/supplies/${supply.id}/movements`)).json(),
  ).toHaveLength(2);
});

test("Inventario: movimiento, asignación, entrega y liberación recuperan sin duplicar", async ({
  page,
  request,
}) => {
  test.setTimeout(180000);
  page.on("dialog", (dialog) => dialog.accept());
  await page.setViewportSize({ width: 1440, height: 960 });
  const record = await fixture(request);
  const before = await (
    await request.get(`${api}/orders/${record.destination.id}`)
  ).json();
  const movements = await loseOnce(
    page,
    `**/api/v1/product-variants/${record.variant.id}/stock-movements`,
  );
  await page.goto(`/products/${record.product.id}`);
  await page
    .getByRole("link", { name: "Ver stock · Variante stock", exact: true })
    .click();
  await page.getByLabel("Cantidad", { exact: true }).fill("4");
  await page.getByLabel("Motivo", { exact: true }).fill("Conteo inicial");
  await page
    .getByLabel("Confirmo el movimiento de stock del producto.", {
      exact: true,
    })
    .check();
  await page
    .getByRole("button", { name: "Registrar movimiento", exact: true })
    .click();
  await retry(page);
  expect(movements()).toBe(2);
  await expect(page.getByTestId("physical")).toHaveText("4.000000 unit");
  const allocations = await loseOnce(page, "**/api/v1/product-allocations");
  await page.goto(`/orders/${record.destination.id}`);
  await page
    .getByRole("link", { name: "Asignaciones y entregas", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Producto", exact: true })
    .selectOption(record.product.id);
  await page
    .getByRole("combobox", { name: "Variante", exact: true })
    .selectOption(record.variant.id);
  await page.getByLabel("Cantidad", { exact: true }).fill("3");
  await page
    .getByLabel("Confirmo la variante, cantidad y destino de la asignación.", {
      exact: true,
    })
    .check();
  await page
    .getByRole("button", { name: "Asignar producto", exact: true })
    .click();
  await retry(page);
  expect(allocations()).toBe(2);
  await expect(page).toHaveURL(/\/inventory\/allocations\/[0-9a-f-]{36}$/);
  const allocationId = page.url().split("/").pop();
  await expect(page.getByTestId("allocated")).toHaveText("3.000000 unit");
  await page.getByLabel("Cantidad a entregar", { exact: true }).fill("4");
  await page
    .getByLabel("Confirmo la entrega física de esta cantidad.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Registrar entrega", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "supera la cantidad pendiente",
  );
  const deliveries = await loseOnce(
    page,
    `**/api/v1/product-allocations/${allocationId}/deliver`,
  );
  await page.getByLabel("Cantidad a entregar", { exact: true }).fill("2");
  await page
    .getByRole("button", { name: "Registrar entrega", exact: true })
    .click();
  await retry(page);
  expect(deliveries()).toBe(2);
  await expect(page.getByTestId("physical")).toHaveText("2.000000 unit");
  await expect(page.getByTestId("allocation-pending")).toContainText(
    "1.000000 unit",
  );
  const releases = await loseOnce(
    page,
    `**/api/v1/product-allocations/${allocationId}/release`,
  );
  await page
    .getByLabel("Confirmo liberar el pendiente de esta asignación.", {
      exact: true,
    })
    .check();
  await page
    .getByRole("button", { name: "Liberar asignación", exact: true })
    .click();
  await retry(page);
  expect(releases()).toBe(2);
  await expect(page.getByTestId("allocation-pending")).toContainText(
    "0.000000 unit",
  );
  await expect(page.getByTestId("delivery-row")).toHaveCount(1);
  const ledger = await (
    await request.get(
      `${api}/product-variants/${record.variant.id}/stock-movements`,
    )
  ).json();
  expect(ledger).toHaveLength(2);
  expect(
    ledger.filter(
      (row: { movement_type: string }) => row.movement_type === "delivery",
    ),
  ).toHaveLength(1);
  expect(
    await (await request.get(`${api}/orders/${record.destination.id}`)).json(),
  ).toEqual(before);
  await axe(page);
  await page
    .getByRole("button", { name: "Cambiar claro / oscuro", exact: true })
    .click();
  await axe(page);
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({ path: "test-results/inventory-allocation-1440.png" });
});

test("Inventario: reservas absolutas y asignación a componente de proyecto", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  page.on("dialog", (dialog) => dialog.accept());
  const record = await fixture(request, true);
  await page.goto(`/production/tasks/${record.task.id}`);
  await page
    .getByRole("link", { name: "Reservas de insumos", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Insumo", exact: true })
    .selectOption(record.supply.id);
  for (const quantity of ["2", "3", "0"]) {
    await page.getByLabel("Cantidad", { exact: true }).fill(quantity);
    await page
      .getByLabel("Confirmo reemplazar la reserva por esta cantidad.", {
        exact: true,
      })
      .check();
    await page
      .getByRole("button", { name: "Guardar reserva", exact: true })
      .click();
    await expect(page.getByTestId("reservation-row")).toHaveCount(1);
    await expect(page.getByTestId("reservation-row")).toContainText(
      `${quantity}.000000 g`,
    );
    if (quantity !== "0")
      await expect(
        page.getByText(
          "El servidor informa faltantes para los compromisos registrados.",
          { exact: true },
        ),
      ).toBeVisible();
  }
  expect(
    await (
      await request.get(`${api}/supplies/${record.supply.id}/movements`)
    ).json(),
  ).toEqual([]);
  await page.goto(`/projects/${record.destination.id}`);
  await page
    .getByRole("link", { name: "Asignaciones y entregas", exact: true })
    .first()
    .click();
  await page
    .getByRole("combobox", { name: "Producto", exact: true })
    .selectOption(record.product.id);
  await page
    .getByRole("combobox", { name: "Variante", exact: true })
    .selectOption(record.variant.id);
  await page.getByLabel("Cantidad", { exact: true }).fill("1");
  await page
    .getByLabel("Confirmo la variante, cantidad y destino de la asignación.", {
      exact: true,
    })
    .check();
  await page
    .getByRole("button", { name: "Asignar producto", exact: true })
    .click();
  await expect(page).toHaveURL(/\/inventory\/allocations\/[0-9a-f-]{36}$/);
  const allocations = await (
    await request.get(
      `${api}/product-allocations?project_component_id=${record.destination.components[0].id}`,
    )
  ).json();
  expect(allocations).toHaveLength(1);
  expect(allocations[0].order_id).toBeNull();
  await expect(
    page.getByText(
      "El servidor informa faltantes para los compromisos registrados.",
      { exact: true },
    ),
  ).toBeVisible();
});
