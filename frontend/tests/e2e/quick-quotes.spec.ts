import AxeBuilder from "@axe-core/playwright";
import { randomUUID } from "node:crypto";
import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
const api = process.env.RRII_E2E_API_BASE!;
async function seed(request: APIRequestContext) {
  const response = await request.post(`${api}/products`, {
    data: {
      name: `Cotizable ${Date.now()}`,
      initial_variant: { name: "Estándar", base_unit: "unit" },
    },
  });
  expect(response.ok(), await response.text()).toBe(true);
  const product = await response.json();
  const variants = await (
    await request.get(`${api}/products/${product.id}/variants`)
  ).json();
  const recipeResponse = await request.post(
    `${api}/products/${product.id}/recipe`,
    { data: { name: "Receta completa" } },
  );
  expect(recipeResponse.ok(), await recipeResponse.text()).toBe(true);
  const recipe = await recipeResponse.json();
  const plan = await request.put(`${api}/recipes/${recipe.id}/plan`, {
    data: {
      steps: [
        {
          key: "make",
          title: "Fabricar",
          is_final_output: true,
          batch_yield: "4",
        },
      ],
    },
  });
  expect(plan.ok(), await plan.text()).toBe(true);
  return { product, variant: variants[0], recipe };
}
async function enter(
  page: Page,
  record: Awaited<ReturnType<typeof seed>>,
  title: string,
) {
  await page.goto(`/quick-quotes/new?product=${record.product.id}`);
  await page.getByLabel("Título del borrador", { exact: true }).fill(title);
  await page
    .getByRole("combobox", { name: "Variante", exact: true })
    .selectOption(record.variant.id);
  await page
    .getByRole("combobox", { name: "Receta", exact: true })
    .selectOption(record.recipe.id);
  await page.getByLabel("Cantidad de productos", { exact: true }).fill("3");
  await page.getByLabel("Markup (%)", { exact: true }).fill("0");
  await page
    .getByRole("combobox", { name: "Paso", exact: true })
    .selectOption("make");
  await page
    .getByRole("button", { name: "Agregar estimación", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Agregar costo adicional", exact: true })
    .click();
  await page
    .getByLabel("Descripción del costo adicional", { exact: true })
    .fill("Preparación");
  await page.getByLabel("Importe", { exact: true }).fill("100.87");
}
for (const width of [360, 1440]) {
  test(`Quick Quote: guardar, revisar y formalizar ${width}px`, async ({
    page,
    request,
  }) => {
    test.setTimeout(240000);
    await page.setViewportSize({ width, height: 900 });
    const runtime: string[] = [];
    page.on("pageerror", (e) => runtime.push(e.message));
    const record = await seed(request),
      title = `Oferta ${width}-${Date.now()}`;
    await enter(page, record, title);
    await page
      .getByRole("button", { name: "Evaluar sin guardar", exact: true })
      .click();
    const preview = page.getByRole("region", {
      name: "Vista previa sin guardar",
      exact: true,
    });
    await expect(
      preview.getByText("ARS 100.8700", { exact: true }),
    ).toBeVisible();
    // La vista previa no crea borradores.
    expect(
      (await (await request.get(`${api}/quick-quotes?limit=100`)).json()).some(
        (row: { definition: { title: string } }) =>
          row.definition.title === title,
      ),
    ).toBe(false);
    for (const mode of ["dark", "light"]) {
      if (mode === "light")
        await page
          .getByRole("button", { name: "Cambiar claro / oscuro" })
          .click();
      await expect(page.locator("html")).toHaveClass(new RegExp(mode));
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
      await page.evaluate(() =>
        window.scrollTo({ top: 0, behavior: "instant" }),
      );
      await page.screenshot({
        path: `test-results/quick-quote-${width}-${mode}.png`,
      });
    }
    await page
      .getByRole("button", { name: "Guardar borrador", exact: true })
      .click();
    await expect(page).toHaveURL(/\/quick-quotes\/[0-9a-f-]{36}$/);
    const id = page.url().split("/").at(-1)!;
    const first = await (await request.get(`${api}/quick-quotes/${id}`)).json();
    expect(first.definition.pricing.target_quantity).toBe("3");
    await page
      .getByRole("button", { name: "Editar última revisión", exact: true })
      .click();
    await page
      .getByLabel("Título del borrador", { exact: true })
      .fill(`${title} revisada`);
    await page.getByLabel("Importe", { exact: true }).fill("200.99");
    await page
      .getByRole("button", { name: "Guardar nueva revisión", exact: true })
      .click();
    await expect(
      page.getByRole("combobox", { name: "Revisión", exact: true }),
    ).toHaveValue("2");
    await page
      .getByRole("combobox", { name: "Revisión", exact: true })
      .selectOption("1");
    const history = page.getByRole("region", { name: /^Historial guardado/ });
    await expect(
      history.getByText("ARS 100.8700", { exact: true }),
    ).toBeVisible();
    const formal = page.getByRole("region", {
      name: "Formalizar la revisión elegida",
      exact: true,
    });
    await formal
      .getByLabel("Total final propuesto (opcional)", { exact: true })
      .fill("1234.87");
    await formal
      .getByRole("button", { name: "Agregar ajuste", exact: true })
      .click();
    await formal
      .getByLabel("Descripción del ajuste", { exact: true })
      .fill("Descuento comercial");
    await formal.getByLabel("Valor del ajuste", { exact: true }).fill("0.87");
    await formal
      .getByRole("button", { name: "Crear presupuesto formal", exact: true })
      .click();
    await expect(
      formal.getByText("Este borrador ya tiene un presupuesto formal.", {
        exact: true,
      }),
    ).toBeVisible();
    const link = await (
      await request.get(`${api}/quick-quotes/${id}/formalization`)
    ).json();
    expect(link.source_revision).toBe(1);
    await formal
      .getByRole("link", { name: "Ver presupuesto formal", exact: true })
      .click();
    await expect(page.getByTestId("formal-total")).toHaveText("ARS 1234.0000");
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
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
    await page.screenshot({
      path: `test-results/formal-quote-${width}-light.png`,
    });
    const quote = await (
      await request.get(`${api}/quotes/${link.quote_id}`)
    ).json();
    expect(quote.status).toBe("draft");
    expect(quote.breakdown.technical_cost).toBe("100.8700");
    expect(quote.source_quick_quote_revision).toBe(1);
    expect(
      (
        await request.post(`${api}/quick-quotes/${id}/formalize`, {
          data: { request_id: randomUUID(), source_revision: 2 },
        })
      ).status(),
    ).toBe(409);
    expect(
      await (await request.get(`${api}/quick-quotes/${id}/revisions/1`)).json(),
    ).toEqual(first);
    await page
      .getByRole("link", { name: "Revisión de origen 1", exact: true })
      .click();
    await expect(
      page.getByRole("combobox", { name: "Revisión", exact: true }),
    ).toHaveValue("1");
    await expect(
      page.getByRole("link", { name: "Ver presupuesto formal", exact: true }),
    ).toBeVisible();
    expect(runtime).toEqual([]);
  });
}

test("respuesta perdida: recarga y reintento conservan la identidad de creación y formalización", async ({
  page,
  request,
}) => {
  test.setTimeout(180000);
  const record = await seed(request);
  await enter(page, record, `Reintento ${Date.now()}`);
  let firstBody: unknown;
  let savedId = "";
  let attempts = 0;
  await page.route("**/api/v1/quick-quotes", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    attempts++;
    const body = route.request().postDataJSON();
    if (attempts === 1) {
      firstBody = body;
      const response = await route.fetch();
      expect(response.status()).toBe(201);
      savedId = (await response.json()).id;
      await route.abort();
    } else {
      expect(body).toEqual(firstBody);
      await route.continue();
    }
  });
  await page
    .getByRole("button", { name: "Guardar borrador", exact: true })
    .click();
  await expect(
    page.getByRole("button", {
      name: "Reintentar solicitud pendiente",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Título del borrador", { exact: true }),
  ).toBeDisabled();
  page.on("dialog", (dialog) => dialog.accept());
  await page.reload();
  await page
    .getByRole("button", {
      name: "Reintentar solicitud pendiente",
      exact: true,
    })
    .click();
  await expect(page).toHaveURL(new RegExp(`/quick-quotes/${savedId}$`));
  expect(attempts).toBe(2);
  expect(
    await (
      await request.get(`${api}/quick-quotes/${savedId}/revisions`)
    ).json(),
  ).toHaveLength(1);
  let formalBody: unknown;
  let formalAttempts = 0;
  await page.route(
    `**/api/v1/quick-quotes/${savedId}/formalize`,
    async (route) => {
      formalAttempts++;
      const body = route.request().postDataJSON();
      if (formalAttempts === 1) {
        formalBody = body;
        const response = await route.fetch();
        expect(response.status()).toBe(201);
        await route.abort();
      } else {
        expect(body).toEqual(formalBody);
        await route.continue();
      }
    },
  );
  await page
    .getByRole("button", { name: "Crear presupuesto formal", exact: true })
    .click();
  await expect(
    page.getByRole("button", {
      name: "Reintentar solicitud pendiente",
      exact: true,
    }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("link", { name: "Ver presupuesto formal", exact: true }),
  ).toBeVisible();
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
  expect(formalAttempts).toBe(2);
});

test("conflicto conserva la edición; historial sin catálogo y evaluación incompleta sin formalizar", async ({
  page,
  request,
}) => {
  test.setTimeout(180000);
  const record = await seed(request);
  await enter(page, record, `Conflicto ${Date.now()}`);
  await page
    .getByRole("button", { name: "Guardar borrador", exact: true })
    .click();
  await expect(page).toHaveURL(/\/quick-quotes\/[0-9a-f-]{36}$/);
  const id = page.url().split("/").at(-1)!;
  await page
    .getByRole("button", { name: "Editar última revisión", exact: true })
    .click();
  await page
    .getByLabel("Título del borrador", { exact: true })
    .fill("Edición local conservada");
  const external = await request.post(`${api}/quick-quotes/${id}/recalculate`, {
    data: { request_id: randomUUID(), expected_revision: 1 },
  });
  expect(external.status()).toBe(200);
  await page
    .getByRole("button", { name: "Guardar nueva revisión", exact: true })
    .click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(
    page.getByLabel("Título del borrador", { exact: true }),
  ).toHaveValue("Edición local conservada");
  await expect(
    page.getByLabel("Título del borrador", { exact: true }),
  ).toBeEnabled();
  await page
    .getByRole("button", { name: "Descartar edición local", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Consultar última revisión", exact: true })
    .click();
  await expect(
    page
      .getByRole("combobox", { name: "Revisión", exact: true })
      .locator("option"),
  ).toHaveCount(2);
  await page
    .getByRole("button", { name: "Recalcular última revisión", exact: true })
    .click();
  await expect(
    page.getByRole("combobox", { name: "Revisión", exact: true }),
  ).toHaveValue("3");
  await page.route("**/api/v1/products**", (route) => route.abort());
  await page.route("**/api/v1/recipes/**", (route) => route.abort());
  await page.reload();
  await expect(
    page.getByRole("region", { name: /^Historial guardado/ }),
  ).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.unroute("**/api/v1/products**");
  await page.unroute("**/api/v1/recipes/**");
  // Un insumo nuevo sin compra tiene costo desconocido; el borrador sigue siendo guardable.
  const supply = await (
    await request.post(`${api}/supplies`, {
      data: {
        name: `Sin costo ${Date.now()}`,
        category: "material",
        base_unit: "g",
      },
    })
  ).json();
  const changed = await request.put(`${api}/recipes/${record.recipe.id}/plan`, {
    data: {
      steps: [
        {
          key: "make",
          title: "Fabricar",
          is_final_output: true,
          supply_inputs: [{ supply_id: supply.id, quantity_per_batch: "1" }],
        },
      ],
    },
  });
  expect(changed.ok(), await changed.text()).toBe(true);
  await page
    .getByRole("button", { name: "Recalcular última revisión", exact: true })
    .click();
  await expect(
    page.getByRole("combobox", { name: "Revisión", exact: true }),
  ).toHaveValue("4");
  await expect(
    page
      .getByRole("region", { name: /^Historial guardado/ })
      .getByText("Evaluación incompleta", { exact: true })
      .first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Crear presupuesto formal", exact: true })
    .click();
  await expect(page.getByRole("alert")).toBeVisible();
  expect(
    (await request.get(`${api}/quick-quotes/${id}/formalization`)).status(),
  ).toBe(404);
});

test("launcher y almacenamiento bloqueado: el reintento permanece en memoria", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const record = await seed(request);
  await page.addInitScript(() => {
    Object.defineProperty(crypto, "randomUUID", { value: undefined });
    Storage.prototype.getItem = () => {
      throw new Error("blocked");
    };
    Storage.prototype.setItem = () => {
      throw new Error("blocked");
    };
    Storage.prototype.removeItem = () => {
      throw new Error("blocked");
    };
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Crear", exact: true }).click();
  await page
    .getByRole("menuitem", { name: "Presupuesto rápido", exact: true })
    .click();
  await expect(page).toHaveURL(/\/quick-quotes\/new$/);
  await expect(
    page.getByText(
      "El navegador no pudo conservar el reintento. Mantené esta pestaña abierta hasta obtener respuesta.",
      { exact: true },
    ),
  ).toBeVisible();
  const title = `En memoria ${Date.now()}`;
  await enter(page, record, title);
  let body: unknown;
  let attempts = 0;
  await page.route("**/api/v1/quick-quotes", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    attempts++;
    if (attempts === 1) {
      body = route.request().postDataJSON();
      await route.abort();
    } else {
      expect(route.request().postDataJSON()).toEqual(body);
      await route.continue();
    }
  });
  await page
    .getByRole("button", { name: "Guardar borrador", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Reintentar solicitud pendiente",
      exact: true,
    })
    .click();
  await expect(page).toHaveURL(/\/quick-quotes\/[0-9a-f-]{36}$/);
  expect(attempts).toBe(2);
  await page
    .getByRole("link", { name: "Volver a presupuestos rápidos", exact: true })
    .click();
  await expect(page.getByRole("link", { name: title, exact: true })).toBeVisible();
});
