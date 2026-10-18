import AxeBuilder from "@axe-core/playwright";
import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
const api = process.env.RRII_E2E_API_BASE!;
async function seed(request: APIRequestContext, project = false) {
  async function post(path: string, data: unknown) {
    const response = await request.post(`${api}${path}`, { data });
    expect(response.ok(), await response.text()).toBe(true);
    return response.json();
  }
  const suffix = `${Date.now()}-${project}`;
  const product = await post("/products", {
    name: `Producción ${suffix}`,
    initial_variant: { name: "Final", base_unit: "unit" },
  });
  const variant = (
    await (await request.get(`${api}/products/${product.id}/variants`)).json()
  )[0];
  const partProduct = await post("/products", {
    name: `Parte ${suffix}`,
    initial_variant: { name: "Parte", base_unit: "unit" },
  });
  const part = (
    await (
      await request.get(`${api}/products/${partProduct.id}/variants`)
    ).json()
  )[0];
  const supply = await post("/supplies", {
    name: `Insumo producción ${suffix}`,
    category: "material",
    base_unit: "g",
  });
  const definition = await post("/option-definitions", {
    name: `Opcional producción ${suffix}`,
  });
  const value = await post(`/option-definitions/${definition.id}/values`, {
    name: "Extra",
  });
  expect(
    (
      await request.put(`${api}/products/${product.id}/configuration`, {
        data: {
          options: [
            { definition_id: definition.id, values: [{ value_id: value.id }] },
          ],
        },
      })
    ).ok(),
  ).toBe(true);
  const recipe = await post(`/products/${product.id}/recipe`, {
    name: `Receta producción ${suffix}`,
  });
  const steps = [
    {
      key: "prepare",
      title: "Preparar piezas",
      output_variant_id: part.id,
      supply_inputs: [{ supply_id: supply.id, quantity_per_batch: "1" }],
    },
    {
      key: "extra",
      title: "Trabajo opcional",
      depends_on: ["prepare"],
      when_selected: { definition_id: definition.id, value_id: value.id },
    },
    {
      key: "pack",
      title: "Armar salida",
      is_final_output: true,
      depends_on: ["prepare"],
      product_inputs: [
        {
          product_variant_id: part.id,
          source_step_key: "prepare",
          quantity_per_batch: "1",
        },
      ],
    },
  ];
  expect(
    (
      await request.put(`${api}/recipes/${recipe.id}/plan`, { data: { steps } })
    ).ok(),
  ).toBe(true);
  const cost = await post("/cost-calculations", {
    extras: [{ description: "Preparación", amount: "100.87", currency: "ARS" }],
  });
  const quote = await post("/quotes", {
    title: `Oferta producción ${suffix}`,
    markup_percentage: "0",
    items: Array.from({ length: project ? 2 : 1 }, (_, i) => ({
      cost_calculation_id: cost.id,
      description: `Componente ${i + 1}`,
      quantity: "1",
    })),
  });
  await post(`/quotes/${quote.id}/approve`, {});
  const conversion = await post(`/quotes/${quote.id}/convert`, {});
  const kind = project ? "projects" : "orders";
  const destination = await (
    await request.get(`${api}/${kind}/${conversion.target_id}`)
  ).json();
  const originId = project ? destination.components[0].id : destination.id;
  const filter = project
    ? `project_component_id=${originId}`
    : `order_id=${originId}`;
  return {
    product,
    variant,
    part,
    supply,
    recipe,
    definition,
    steps,
    quote,
    destination,
    kind,
    originId,
    filter,
  };
}
type Record = Awaited<ReturnType<typeof seed>>;
async function openPlanner(page: Page, record: Record) {
  await page.goto(`/${record.kind}/${record.destination.id}`);
  await page
    .getByRole("link", { name: "Planificar producción", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Nuevo plan de producción",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("combobox", { name: "Producto", exact: true })
    .selectOption(record.product.id);
  await page
    .getByRole("combobox", { name: "Variante", exact: true })
    .selectOption(record.variant.id);
  await page
    .getByRole("combobox", { name: "Receta", exact: true })
    .selectOption(record.recipe.id);
  await expect(
    page.getByLabel("Cantidad objetivo", { exact: true }),
  ).toHaveValue("");
  await page.getByLabel("Cantidad objetivo", { exact: true }).fill("2");
  await page
    .getByRole("button", { name: "Previsualizar receta", exact: true })
    .click();
  await expect(page.getByTestId("production-preview")).toContainText("prepare");
  await expect(page.getByTestId("production-preview")).toContainText(
    "Pasos omitidos: extra",
  );
}
async function createPlan(
  page: Page,
  record: Record,
  request: APIRequestContext,
) {
  await page
    .getByLabel(
      "Confirmo la configuración, cantidad y efectos del nuevo plan.",
      { exact: true },
    )
    .check();
  await page
    .getByRole("button", { name: "Crear plan de producción", exact: true })
    .click();
  await expect(page).toHaveURL(/\/production\/plans\/[0-9a-f-]{36}$/);
  const id = page.url().split("/").pop();
  return await (await request.get(`${api}/production-plans/${id}`)).json();
}
async function start(page: Page) {
  await page
    .getByRole("button", { name: "Iniciar intento", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Cerrar intento", exact: true }),
  ).toBeVisible();
}
async function enterClose(
  page: Page,
  good: string,
  consumed: string,
  failed = "0",
) {
  await page.getByLabel("Unidades buenas", { exact: true }).fill(good);
  await page.getByLabel("Unidades fallidas", { exact: true }).fill(failed);
  if (failed !== "0")
    await page
      .getByRole("combobox", { name: "Motivo de falla", exact: true })
      .selectOption("quality_failure");
  await page.getByLabel("Consumo total", { exact: true }).fill(consumed);
  await page
    .getByLabel(
      "Confirmo que los resultados y consumos corresponden a este intento.",
      { exact: true },
    )
    .check();
}
async function close(page: Page, good: string, consumed: string, failed = "0") {
  await enterClose(page, good, consumed, failed);
  await page
    .getByRole("button", { name: "Cerrar intento", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Cerrar intento", exact: true }),
  ).toHaveCount(0);
}
for (const width of [360, 1440]) {
  test(`Producción: plan, dependencias, consumos y stock ${width}px`, async ({
    page,
    request,
  }) => {
    test.setTimeout(180000);
    page.on("dialog", (dialog) => dialog.accept());
    await page.setViewportSize({ width, height: 960 });
    const record = await seed(request, width === 1440);
    const before = await (
      await request.get(`${api}/${record.kind}/${record.destination.id}`)
    ).json();
    await openPlanner(page, record);
    expect(
      await (
        await request.get(`${api}/production-tasks?${record.filter}`)
      ).json(),
    ).toEqual([]);
    // Cambiar una entrada descarta la preview; no habilita crear con resultados obsoletos.
    await page.getByLabel("Cantidad objetivo", { exact: true }).fill("3");
    await expect(page.getByTestId("production-preview")).toHaveCount(0);
    await page.getByLabel("Cantidad objetivo", { exact: true }).fill("2");
    await page
      .getByRole("button", { name: "Previsualizar receta", exact: true })
      .click();
    await expect(page.getByTestId("production-preview")).toBeVisible();
    if (width === 1440) {
      await page
        .getByLabel("Reservar insumos al crear", { exact: true })
        .uncheck();
      await page
        .getByLabel("Asignar salida al destino al crear", { exact: true })
        .uncheck();
    }
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
          .analyze()
      ).violations,
    ).toEqual([]);
    const plan = await createPlan(page, record, request);
    expect(plan.tasks).toHaveLength(2);
    expect(!!plan.allocation_id).toBe(width === 360);
    const prepare = plan.tasks.find(
      (task: { recipe_step_key: string }) => task.recipe_step_key === "prepare",
    );
    const pack = plan.tasks.find(
      (task: { recipe_step_key: string }) => task.recipe_step_key === "pack",
    );
    const reservations = await (
      await request.get(
        `${api}/production-tasks/${prepare.id}/supply-reservations`,
      )
    ).json();
    expect(reservations).toHaveLength(width === 360 ? 1 : 0);
    const snapshot = plan.snapshot;
    expect(
      (
        await request.put(`${api}/recipes/${record.recipe.id}/plan`, {
          data: {
            steps: [
              {
                key: "replacement",
                title: "Receta posterior",
                is_final_output: true,
              },
            ],
          },
        })
      ).ok(),
    ).toBe(true);
    await page
      .getByRole("link", { name: new RegExp(`${pack.code} · Armar salida`) })
      .click();
    await page
      .getByRole("button", { name: "Iniciar intento", exact: true })
      .click();
    await expect(page.getByRole("alert")).toContainText("prerrequisitos");
    await page
      .getByRole("link", {
        name: new RegExp(`${prepare.code} · Preparar piezas`),
      })
      .click();
    await start(page);
    await expect(
      page.getByText(
        /ingresa las unidades buenas de la salida inventariable al stock/,
      ),
    ).toBeVisible();
    await close(page, "0", "0.25", "1");
    await page
      .getByLabel("Confirmo el cambio de estado de esta tarea.", {
        exact: true,
      })
      .check();
    await page
      .getByRole("button", { name: "Pausar tarea", exact: true })
      .click();
    await expect(page.getByTestId("task-status")).toHaveText("Pausada");
    await page
      .getByLabel("Confirmo el cambio de estado de esta tarea.", {
        exact: true,
      })
      .check();
    await page
      .getByRole("button", { name: "Reanudar tarea", exact: true })
      .click();
    await expect(page.getByTestId("task-status")).toHaveText("En curso");
    await start(page);
    await close(page, "2", "2");
    await expect(page.getByTestId("task-status")).toHaveText(
      "Finalizada físicamente",
    );
    await page.getByRole("link", { name: "Abrir plan", exact: true }).click();
    await page
      .getByRole("link", { name: new RegExp(`${pack.code} · Armar salida`) })
      .click();
    await start(page);
    await close(page, "2", "2");
    await expect(page.getByTestId("task-status")).toHaveText(
      "Finalizada físicamente",
    );
    await page
      .getByRole("button", { name: "Ver resultado y consumos", exact: true })
      .click();
    await expect(
      page.getByText("Consumos registrados", { exact: true }),
    ).toBeVisible();
    for (const theme of ["dark", "light"]) {
      if (theme === "light")
        await page
          .getByRole("button", { name: "Cambiar claro / oscuro", exact: true })
          .click();
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
      await page.evaluate(() => {
        (document.activeElement as HTMLElement | null)?.blur();
        window.scrollTo({ top: 0, behavior: "instant" });
      });
      await page.screenshot({
        path: `test-results/production-${width}-${theme}.png`,
        fullPage: false,
      });
    }
    const stock = await (
      await request.get(`${api}/product-variants/${record.variant.id}/stock`)
    ).json();
    expect(stock.physical_quantity).toBe("2.000000");
    expect(stock.allocated_quantity).toBe(width === 360 ? "2.000000" : "0");
    const partStock = await (
      await request.get(`${api}/product-variants/${record.part.id}/stock`)
    ).json();
    expect(partStock.physical_quantity).toMatch(/^0(?:\.0+)?$/);
    expect(
      (await (await request.get(`${api}/production-plans/${plan.id}`)).json())
        .snapshot,
    ).toEqual(snapshot);
    expect(
      await (
        await request.get(`${api}/${record.kind}/${record.destination.id}`)
      ).json(),
    ).toEqual(before);
    await page.goto(
      `/production?${width === 360 ? "order" : "component"}=${record.originId}`,
    );
    await page
      .getByRole("combobox", { name: "Estado", exact: true })
      .selectOption("physically_completed");
    await page
      .getByRole("button", { name: "Aplicar filtros", exact: true })
      .click();
    await expect(
      page.getByRole("link", { name: new RegExp(prepare.code) }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: new RegExp(pack.code) }),
    ).toBeVisible();
  });
}

test("Producción: recuperar creación, inicio y cierre sin duplicar; cancelar tarea conserva asignación", async ({
  page,
  request,
}) => {
  test.setTimeout(180000);
  page.on("dialog", (dialog) => dialog.accept());
  const record = await seed(request);
  expect(
    (
      await request.put(`${api}/recipes/${record.recipe.id}/plan`, {
        data: {
          steps: [
            {
              key: "final",
              title: "Trabajo recuperable",
              is_final_output: true,
              supply_inputs: [
                { supply_id: record.supply.id, quantity_per_batch: "1" },
              ],
            },
          ],
        },
      })
    ).ok(),
  ).toBe(true);
  async function loseOnce(pattern: string) {
    let count = 0;
    let original: unknown;
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
  const creates = await loseOnce(
    `**/api/v1/orders/${record.destination.id}/production-plans`,
  );
  await page.goto(`/production/plans/new?order=${record.destination.id}`);
  await page
    .getByRole("combobox", { name: "Producto", exact: true })
    .selectOption(record.product.id);
  await page
    .getByRole("combobox", { name: "Variante", exact: true })
    .selectOption(record.variant.id);
  await page
    .getByRole("combobox", { name: "Receta", exact: true })
    .selectOption(record.recipe.id);
  await page.getByLabel("Cantidad objetivo", { exact: true }).fill("2");
  await page
    .getByRole("button", { name: "Previsualizar receta", exact: true })
    .click();
  await expect(page.getByTestId("production-preview")).toBeVisible();
  await page
    .getByLabel(
      "Confirmo la configuración, cantidad y efectos del nuevo plan.",
      { exact: true },
    )
    .check();
  await page
    .getByRole("button", { name: "Crear plan de producción", exact: true })
    .click();
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
  await expect(page).toHaveURL(/\/production\/plans\/[0-9a-f-]{36}$/);
  expect(creates()).toBe(2);
  const tasks = await (
    await request.get(`${api}/production-tasks?${record.filter}`)
  ).json();
  expect(tasks).toHaveLength(1);
  const task = tasks[0];
  const starts = await loseOnce(`**/api/v1/production-tasks/${task.id}/runs`);
  await page.getByRole("link", { name: new RegExp(task.code) }).click();
  await page
    .getByRole("button", { name: "Iniciar intento", exact: true })
    .click();
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
  expect(starts()).toBe(2);
  const runs = await (
    await request.get(`${api}/production-tasks/${task.id}/runs`)
  ).json();
  expect(runs).toHaveLength(1);
  const closes = await loseOnce(
    `**/api/v1/production-runs/${runs[0].id}/close`,
  );
  await enterClose(page, "1", "1");
  await page
    .getByRole("button", { name: "Cerrar intento", exact: true })
    .click();
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
  expect(closes()).toBe(2);
  expect(
    await (
      await request.get(
        `${api}/production-runs/${runs[0].id}/supply-consumptions`,
      )
    ).json(),
  ).toHaveLength(1);
  expect(
    await (
      await request.get(
        `${api}/product-variants/${record.variant.id}/stock-movements`,
      )
    ).json(),
  ).toHaveLength(1);
  await page
    .getByLabel("Confirmo el cambio de estado de esta tarea.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Cancelar tarea", exact: true })
    .click();
  await expect(page.getByTestId("task-status")).toHaveText("Cancelada");
  const stock = await (
    await request.get(`${api}/product-variants/${record.variant.id}/stock`)
  ).json();
  expect(stock.physical_quantity).toBe("1.000000");
  expect(stock.allocated_quantity).toBe("2.000000");
  const reservations = await (
    await request.get(`${api}/production-tasks/${task.id}/supply-reservations`)
  ).json();
  expect(
    reservations.every((row: { quantity: string }) =>
      /^0(?:\.0+)?$/.test(row.quantity),
    ),
  ).toBe(true);
});

test("Producción: preview tardía, máquina guardada y conflicto con intento abierto", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  page.on("dialog", (dialog) => dialog.accept());
  const record = await seed(request);
  const existingMachines = await (await request.get(`${api}/machines`)).json();
  let machine = existingMachines.find((row: { active: boolean }) => row.active);
  if (!machine) {
    const response = await request.post(`${api}/machines`, {
      data: { name: "E2E Producción UI", machine_type: "fdm_printer" },
    });
    expect(response.ok(), await response.text()).toBe(true);
    machine = await response.json();
  }
  await openPlanner(page, record);
  let release!: () => void;
  let delivered!: () => void;
  const delayed = new Promise<void>((resolve) => {
    release = resolve;
  });
  const completed = new Promise<void>((resolve) => {
    delivered = resolve;
  });
  await page.route(
    `**/api/v1/recipes/${record.recipe.id}/production-preview`,
    async (route) => {
      const response = await route.fetch();
      await delayed;
      await route.fulfill({ response });
      delivered();
    },
    { times: 1 },
  );
  const requested = page.waitForRequest(
    `**/api/v1/recipes/${record.recipe.id}/production-preview`,
  );
  await page
    .getByRole("button", { name: "Previsualizar receta", exact: true })
    .click();
  await requested;
  await page.getByLabel("Cantidad objetivo", { exact: true }).fill("1");
  release();
  await completed;
  await expect(
    page.getByRole("button", { name: "Previsualizar receta", exact: true }),
  ).toBeEnabled();
  await expect(page.getByTestId("production-preview")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Crear plan de producción", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("combobox", { name: "Modo de selección", exact: true })
    .selectOption("explicit");
  await page
    .getByRole("button", { name: "Previsualizar receta", exact: true })
    .click();
  await expect(page.getByTestId("production-preview")).toBeVisible();
  await page
    .getByRole("combobox", { name: "Máquina · prepare", exact: true })
    .selectOption(machine.id);
  const plan = await createPlan(page, record, request);
  expect(plan.snapshot.machine_assignments).toEqual({ prepare: machine.id });
  const task = plan.tasks.find(
    (row: { recipe_step_key: string }) => row.recipe_step_key === "prepare",
  );
  await page.getByRole("link", { name: new RegExp(task.code) }).click();
  await start(page);
  const [run] = await (
    await request.get(`${api}/production-tasks/${task.id}/runs`)
  ).json();
  expect(run.machine_id).toBe(machine.id);
  await page
    .getByLabel("Confirmo el cambio de estado de esta tarea.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Cancelar tarea", exact: true })
    .click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByTestId("task-status")).toHaveText("En curso");
  await close(page, "0", "0.5", "1");
  await page.route(
    `**/api/v1/production-tasks/${task.id}/cancel`,
    async (route) => {
      const response = await route.fetch();
      expect(response.ok()).toBe(true);
      await route.abort();
    },
    { times: 1 },
  );
  await page
    .getByLabel("Confirmo el cambio de estado de esta tarea.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Cancelar tarea", exact: true })
    .click();
  await expect(page.getByTestId("task-status")).toHaveText("Cancelada");
  await expect(page.getByRole("alert")).toContainText("Se consultó el estado");
  const response = await request.post(
    `${api}/orders/${record.destination.id}/cancel`,
  );
  expect(response.ok(), await response.text()).toBe(true);
  await page.goto(`/production/plans/new?order=${record.destination.id}`);
  await expect(page.getByRole("alert")).toContainText(
    "El destino está cancelado",
  );
  await expect(
    page.getByRole("button", { name: "Crear plan de producción", exact: true }),
  ).toHaveCount(0);
});
