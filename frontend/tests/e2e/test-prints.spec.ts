import AxeBuilder from "@axe-core/playwright";
import { randomUUID } from "node:crypto";
import {
  expect,
  test,
  type APIRequestContext,
  type Locator,
} from "@playwright/test";
const api = process.env.RRII_E2E_API_BASE!;
async function seed(request: APIRequestContext) {
  async function post(path: string, data: unknown) {
    const response = await request.post(`${api}${path}`, { data });
    expect(response.ok(), await response.text()).toBe(true);
    return response.json();
  }
  const suffix = Date.now();
  const product = await post("/products", {
    name: `Prueba ${suffix}`,
    initial_variant: { name: "Final", base_unit: "unit" },
  });
  const variant = (
    await (await request.get(`${api}/products/${product.id}/variants`)).json()
  )[0];
  const componentProduct = await post("/products", {
    name: `Componente ${suffix}`,
    initial_variant: { name: "Componente", base_unit: "unit" },
  });
  const component = (
    await (
      await request.get(`${api}/products/${componentProduct.id}/variants`)
    ).json()
  )[0];
  const supply = await post("/supplies", {
    name: `Material prueba ${suffix}`,
    category: "material",
    base_unit: "g",
  });
  const machines = await (await request.get(`${api}/machines`)).json();
  const machine =
    machines.find(
      (row: { name: string; active: boolean }) =>
        row.name === "E2E Test Print UI" && row.active,
    ) ??
    (await post("/machines", {
      name: "E2E Test Print UI",
      machine_type: "fdm_printer",
    }));
  const service = await post("/service-definitions", {
    name: `Acabado ${suffix}`,
    action_template: "Terminar {quantity} de {product}",
  });
  const option = await post("/option-definitions", {
    name: `Terminación prueba ${suffix}`,
  });
  const value = await post(`/option-definitions/${option.id}/values`, {
    name: "Mate",
  });
  const alternate = await post(`/option-definitions/${option.id}/values`, {
    name: "Brillo",
  });
  const configured = await request.put(
    `${api}/products/${product.id}/configuration`,
    {
      data: {
        options: [
          {
            definition_id: option.id,
            values: [
              { value_id: value.id, default_quantity: "1" },
              { value_id: alternate.id },
            ],
          },
        ],
      },
    },
  );
  expect(configured.ok(), await configured.text()).toBe(true);
  const recipe = await post(`/products/${product.id}/recipe`, {
    name: `Receta prueba ${suffix}`,
  });
  const response = await request.put(`${api}/recipes/${recipe.id}/plan`, {
    data: {
      steps: [
        {
          key: "extra",
          title: "Acabado opcional",
          depends_on: ["print"],
          when_selected: { definition_id: option.id, value_id: alternate.id },
        },
        {
          key: "print",
          title: "Imprimir",
          task_type: "fdm_print",
          output_variant_id: component.id,
          supply_inputs: [{ supply_id: supply.id, quantity_per_batch: "0.5" }],
        },
        {
          key: "service",
          title: "Terminar",
          kind: "service",
          service_definition_id: service.id,
          depends_on: ["print"],
        },
        { key: "wait", title: "Secar", kind: "wait", depends_on: ["service"] },
        {
          key: "pack",
          title: "Armar",
          task_type: "assembly",
          is_final_output: true,
          depends_on: ["wait", "print"],
          product_inputs: [
            {
              product_variant_id: component.id,
              source_step_key: "print",
              quantity_per_batch: "1",
            },
          ],
        },
      ],
    },
  });
  expect(response.ok(), await response.text()).toBe(true);
  return {
    product,
    variant,
    component,
    supply,
    machine,
    recipe,
    option,
    value,
  };
}
async function start(step: Locator, machine?: string) {
  if (machine)
    await step
      .getByRole("combobox", { name: "Máquina del intento", exact: true })
      .selectOption(machine);
  await step
    .getByRole("button", { name: "Iniciar intento", exact: true })
    .click();
  await expect(
    step.getByRole("button", { name: "Cerrar intento", exact: true }),
  ).toBeVisible();
}
async function close(
  step: Locator,
  good: string,
  consumed?: string,
  failed = "0",
) {
  await step.getByLabel("Unidades buenas", { exact: true }).fill(good);
  await step.getByLabel("Unidades fallidas", { exact: true }).fill(failed);
  if (failed !== "0")
    await step
      .getByRole("combobox", { name: "Motivo de falla", exact: true })
      .selectOption("quality_failure");
  if (consumed)
    await step.getByLabel("Consumo total", { exact: true }).fill(consumed);
  if (failed !== "0" && consumed)
    await step
      .getByLabel("Desperdicio incluido", { exact: true })
      .fill(consumed);
  await step
    .getByLabel(
      "Confirmo que los resultados y consumos corresponden a este intento.",
      { exact: true },
    )
    .check();
  await step
    .getByRole("button", { name: "Cerrar intento", exact: true })
    .click();
  await expect(
    step.getByRole("button", { name: "Cerrar intento", exact: true }),
  ).toHaveCount(0);
}
for (const width of [360, 1440]) {
  test(`Test print: receta completa, intentos y promoción única ${width}px`, async ({
    page,
    request,
  }) => {
    test.setTimeout(240000);
    await page.setViewportSize({ width, height: 900 });
    const record = await seed(request),
      runtime: string[] = [];
    page.on("pageerror", (e) => runtime.push(e.message));
    await page.goto(`/products/${record.product.id}`);
    await page
      .getByRole("link", { name: "Probar receta · Final", exact: true })
      .click();
    await page
      .getByRole("combobox", { name: "Receta", exact: true })
      .selectOption(record.recipe.id);
    await page.getByLabel("Cantidad objetivo", { exact: true }).fill("2");
    if (width === 1440) {
      await page
        .getByRole("combobox", { name: "Modo de selección", exact: true })
        .selectOption("explicit");
      await page
        .getByRole("button", { name: "Agregar selección", exact: true })
        .click();
      await page
        .getByRole("combobox", { name: "Valor", exact: true })
        .selectOption(record.value.id);
      await page.getByLabel("Cantidad seleccionada", { exact: true }).fill("2");
    }

    await page
      .getByRole("button", { name: "Previsualizar receta", exact: true })
      .click();
    await expect(page.getByTestId("recipe-preview").locator("li")).toHaveCount(
      4,
    );
    await expect(page.getByTestId("recipe-preview")).toContainText("extra");
    expect(
      await (
        await request.get(`${api}/test-prints?variant_id=${record.variant.id}`)
      ).json(),
    ).toEqual([]);
    await page.getByLabel("Cantidad objetivo", { exact: true }).fill("3");
    await expect(page.getByTestId("recipe-preview")).toHaveCount(0);
    await page.getByLabel("Cantidad objetivo", { exact: true }).fill("2");

    await page
      .getByRole("button", { name: "Crear prueba completa", exact: true })
      .click();
    await expect(page).toHaveURL(/\/test-prints\/[0-9a-f-]{36}$/);
    const id = page.url().split("/").at(-1)!;
    const stored = await (await request.get(`${api}/test-prints/${id}`)).json();
    expect(stored.steps).toHaveLength(4);
    await expect(
      page
        .getByRole("region", { name: /^Paso / })
        .first()
        .getByRole("heading", { level: 2 }),
    ).toHaveText("Imprimir");
    expect(stored.snapshot.omitted_step_keys).toEqual(["extra"]);
    expect(
      stored.snapshot.configuration.selections[0].values[0].quantity,
    ).toMatch(width === 1440 ? /^2(?:\.0+)?$/ : /^1(?:\.0+)?$/);

    const print = page.getByRole("region", { name: "Paso print", exact: true }),
      service = page.getByRole("region", { name: "Paso service", exact: true }),
      wait = page.getByRole("region", { name: "Paso wait", exact: true }),
      pack = page.getByRole("region", { name: "Paso pack", exact: true });
    await service
      .getByRole("button", { name: "Iniciar intento", exact: true })
      .click();
    await expect(service.getByRole("alert")).toContainText("prerrequisitos");
    await start(print, record.machine.id);
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
          .analyze()
      ).violations,
    ).toEqual([]);
    // El backend protege también la ocupación de la máquina frente a otra prueba.
    const other = await request.post(`${api}/test-prints`, {
      data: {
        request_id: randomUUID(),
        recipe_id: record.recipe.id,
        variant_id: record.variant.id,
        target_quantity: "1",
      },
    });
    expect(other.status()).toBe(201);
    const otherId = (await other.json()).id;
    expect(
      (
        await request.post(`${api}/test-prints/${otherId}/steps/print/runs`, {
          data: { request_id: randomUUID(), machine_id: record.machine.id },
        })
      ).status(),
    ).toBe(409);
    const cancel = page.getByRole("region", {
      name: "Cancelar prueba",
      exact: true,
    });
    await cancel
      .getByLabel("Confirmo cancelar esta prueba sin revertir sus consumos.", {
        exact: true,
      })
      .check();
    await cancel
      .getByRole("button", { name: "Cancelar prueba", exact: true })
      .click();
    await expect(cancel.getByRole("alert")).toBeVisible();
    await close(print, "0", "0.25", "1");
    await start(print, record.machine.id);
    await close(print, "1", "0.5");
    await expect(page.getByTestId("test-status")).toHaveText("Abierta");
    await start(print, record.machine.id);
    await close(print, "1", "0.5");
    await start(service);
    await close(service, "2");
    await start(wait);
    await close(wait, "2");
    await expect(page.getByTestId("test-status")).toHaveText("Abierta");
    await start(pack);
    await close(pack, "2", "2");
    await expect(page.getByTestId("test-status")).toHaveText("Completada");
    const movements = async (variant: string) =>
      await (
        await request.get(`${api}/product-variants/${variant}/stock-movements`)
      ).json();
    expect(await movements(record.variant.id)).toEqual([]);
    expect(await movements(record.component.id)).toEqual([]);
    const packRun = (
      await (
        await request.get(`${api}/test-prints/${id}/steps/pack/runs`)
      ).json()
    )[0];
    const consumptions = await (
      await request.get(
        `${api}/production-runs/${packRun.id}/product-consumptions`,
      )
    ).json();
    expect(consumptions[0].internal_source_step_id).toBe(
      stored.steps.find((s: { key: string }) => s.key === "print").id,
    );
    expect(consumptions[0].consumed).toBe("2.000000");
    const promotion = page.getByRole("region", {
      name: "Promoción explícita a stock",
      exact: true,
    });
    await promotion
      .getByLabel("Cantidad a promover", { exact: true })
      .fill("1");
    await promotion
      .getByLabel(
        "Confirmo la cantidad y que esta será la única promoción de la prueba.",
        { exact: true },
      )
      .check();
    await promotion
      .getByRole("button", { name: "Promover a stock", exact: true })
      .click();
    await expect(promotion.getByRole("status")).toContainText(
      "Promoción registrada",
    );
    await expect(page.getByTestId("promoted-quantity")).toHaveText(
      "Cantidad ingresada a stock: 1.000000 unit",
    );
    const stock = await movements(record.variant.id);
    expect(stock).toHaveLength(1);
    expect(stock[0].quantity).toBe("1.000000");
    expect(
      (
        await request.post(`${api}/test-prints/${id}/promote`, {
          data: { request_id: randomUUID(), quantity: "1" },
        })
      ).status(),
    ).toBe(409);
    await page.reload();
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
        path: `test-results/test-print-${width}-${mode}.png`,
      });
    }
    expect(runtime).toEqual([]);
  });
}

test("Test print: respuestas perdidas al crear, iniciar, cerrar y promover se recuperan sin duplicar", async ({
  page,
  request,
}) => {
  test.setTimeout(180000);
  const record = await seed(request);
  // Usar receta breve para centrar la prueba en recuperación, con consumo real.
  const response = await request.put(
    `${api}/recipes/${record.recipe.id}/plan`,
    {
      data: {
        steps: [
          {
            key: "final",
            title: "Final",
            is_final_output: true,
            supply_inputs: [
              { supply_id: record.supply.id, quantity_per_batch: "1" },
            ],
          },
        ],
      },
    },
  );
  expect(response.ok()).toBe(true);
  page.on("dialog", (dialog) => dialog.accept());
  async function loseOnce(pattern: string) {
    let count = 0;
    let original: unknown;
    await page.route(pattern, async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      count++;
      const body = route.request().postDataJSON();
      if (count === 1) {
        original = body;
        const result = await route.fetch();
        expect(result.ok(), await result.text()).toBe(true);
        await route.abort();
      } else {
        expect(body).toEqual(original);
        await route.continue();
      }
    });
    return () => count;
  }
  const creates = await loseOnce("**/api/v1/test-prints");
  await page.goto(`/test-prints/new?variant=${record.variant.id}`);
  await page
    .getByRole("combobox", { name: "Receta", exact: true })
    .selectOption(record.recipe.id);
  await page
    .getByRole("button", { name: "Crear prueba completa", exact: true })
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
  await expect(page).toHaveURL(/\/test-prints\/[0-9a-f-]{36}$/);
  expect(creates()).toBe(2);
  const id = page.url().split("/").at(-1)!;
  const starts = await loseOnce(`**/api/v1/test-prints/${id}/steps/final/runs`);
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
    await request.get(`${api}/test-prints/${id}/steps/final/runs`)
  ).json();
  expect(runs).toHaveLength(1);
  const closes = await loseOnce(
    `**/api/v1/production-runs/${runs[0].id}/close`,
  );
  await page.getByLabel("Unidades buenas", { exact: true }).fill("1");
  await page.getByLabel("Consumo total", { exact: true }).fill("1.000001");
  await page
    .getByLabel(
      "Confirmo que los resultados y consumos corresponden a este intento.",
      { exact: true },
    )
    .check();
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
  const consumed = await (
    await request.get(
      `${api}/production-runs/${runs[0].id}/supply-consumptions`,
    )
  ).json();
  expect(consumed).toHaveLength(1);
  expect(consumed[0].consumed).toBe("1.000001");
  const promotes = await loseOnce(`**/api/v1/test-prints/${id}/promote`);
  await page.getByLabel("Cantidad a promover", { exact: true }).fill("1");
  await page
    .getByLabel(
      "Confirmo la cantidad y que esta será la única promoción de la prueba.",
      { exact: true },
    )
    .check();
  await page
    .getByRole("button", { name: "Promover a stock", exact: true })
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
  expect(promotes()).toBe(2);
  expect(
    await (
      await request.get(
        `${api}/product-variants/${record.variant.id}/stock-movements`,
      )
    ).json(),
  ).toHaveLength(1);
});

test("Test print: cancelación explícita y lectura sin catálogo", async ({
  page,
  request,
}) => {
  const record = await seed(request);
  const created = await request.post(`${api}/test-prints`, {
    data: {
      request_id: randomUUID(),
      recipe_id: record.recipe.id,
      variant_id: record.variant.id,
      target_quantity: "1",
    },
  });
  expect(created.status()).toBe(201);
  const original = await created.json();
  await page.route("**/api/v1/product-variants/**", (route) => route.abort());
  await page.route("**/api/v1/supplies**", (route) => route.abort());
  await page.goto(`/test-prints/${original.id}`);
  await expect(
    page.getByRole("heading", { name: "Imprimir", exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Confirmo cancelar esta prueba sin revertir sus consumos.", {
      exact: true,
    })
    .check();
  await page
    .getByRole("button", { name: "Cancelar prueba", exact: true })
    .click();
  await expect(page.getByTestId("test-status")).toHaveText("Cancelada");
  await expect(
    page.getByRole("button", { name: "Promover a stock", exact: true }),
  ).toBeDisabled();
  const saved = await (
    await request.get(`${api}/test-prints/${original.id}`)
  ).json();
  expect(saved.snapshot).toEqual(original.snapshot);
  await page
    .getByRole("link", { name: "Volver a pruebas", exact: true })
    .click();
  await expect(
    page.getByRole("link", { name: record.recipe.name, exact: true }),
  ).toBeVisible();
});
