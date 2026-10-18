import AxeBuilder from "@axe-core/playwright";
import { test, expect, type APIRequestContext } from "@playwright/test";
const api = process.env.RRII_E2E_API_BASE!;
test.use({ timezoneId: "UTC" });
async function post(
  request: APIRequestContext,
  path: string,
  data: unknown = {},
) {
  const r = await request.post(`${api}${path}`, { data });
  expect(r.ok(), await r.text()).toBe(true);
  return r.json();
}
async function seed(request: APIRequestContext, project = false) {
  const cost = await post(request, "/cost-calculations", {
    extras: [{ description: "Manual", amount: "100", currency: "ARS" }],
  });
  const quote = await post(request, "/quotes", {
    title: `Manual ${Date.now()}`,
    items: Array.from({ length: project ? 2 : 1 }, (_, i) => ({
      cost_calculation_id: cost.id,
      description: `Pieza ${i}`,
      quantity: "1",
    })),
  });
  await post(request, `/quotes/${quote.id}/approve`);
  const converted = await post(request, `/quotes/${quote.id}/convert`);
  return (
    await request.get(
      `${api}/${project ? "projects" : "orders"}/${converted.target_id}`,
    )
  ).json();
}
test("alta, edición, consumo y cierre manual con precisión", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const order = await seed(request);
  const product = await post(request, "/products", {
    name: `Salida manual ${Date.now()}`,
    initial_variant: { name: "Terminada", base_unit: "unit" },
  });
  const variant = (
    await (await request.get(`${api}/products/${product.id}/variants`)).json()
  )[0];
  const supply = await post(request, "/supplies", {
    name: `Manual supply ${Date.now()}`,
    category: "material",
    base_unit: "g",
  });
  await post(request, `/supplies/${supply.id}/adjustments`, {
    direction: "in",
    quantity: "10",
    reason: "Fixture",
    occurred_at: new Date(Date.now() - 1000).toISOString(),
  });
  await page.setViewportSize({ width: 360, height: 960 });
  await page.goto(`/orders/${order.id}`);
  await page
    .getByRole("link", { name: "Crear tarea manual", exact: true })
    .click();
  await page
    .getByLabel("Título de tarea", { exact: true })
    .fill("Trabajo manual");
  await page
    .getByLabel("Cantidad planificada", { exact: true })
    .fill("1.000001");
  await page
    .getByRole("combobox", {
      name: "Producto de salida (opcional)",
      exact: true,
    })
    .selectOption(product.id);
  await page
    .getByRole("combobox", { name: "Variante de salida", exact: true })
    .selectOption(variant.id);
  await page.getByLabel("Confirmo la planificación de la tarea.").check();
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page
    .getByRole("button", { name: "Crear tarea manual", exact: true })
    .click();
  await expect(page).toHaveURL(/\/production\/tasks\/[0-9a-f-]{36}$/);
  const id = page.url().split("/").at(-1)!;
  await page
    .getByRole("link", { name: "Editar planificación", exact: true })
    .click();
  await page
    .getByLabel("Notas operativas", { exact: true })
    .fill("Nota conservada");
  await page
    .getByRole("combobox", { name: "Prioridad", exact: true })
    .selectOption("high");
  await page.getByLabel("Confirmo la planificación de la tarea.").check();
  await page
    .getByRole("button", { name: "Guardar tarea", exact: true })
    .click();
  await expect(page).toHaveURL(`/production/tasks/${id}`);
  await page.getByText("Opciones de ejecución", { exact: true }).click();
  await page
    .getByLabel("Inicio real (opcional)", { exact: true })
    .fill("2026-10-01T10:00");
  await page
    .getByLabel("Reemplazar parámetros para este intento", { exact: true })
    .check();
  await page
    .getByLabel("Parámetros del intento (objeto JSON)", { exact: true })
    .fill('{"speed":"25.000001"}');
  await page
    .getByRole("button", { name: "Iniciar intento", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Insumo consumido", exact: true })
    .selectOption(supply.id);
  await page
    .getByRole("button", { name: "Agregar consumo de insumo", exact: true })
    .click();
  await page.getByLabel("Unidades buenas", { exact: true }).fill("1.000001");
  await page.getByLabel("Consumo total", { exact: true }).fill("2.123456");
  await page
    .getByLabel(
      "Confirmo que los resultados y consumos corresponden a este intento.",
    )
    .check();
  await page
    .getByRole("button", { name: "Cerrar intento", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Cerrar intento", exact: true }),
  ).toHaveCount(0);
  const task = await (
    await request.get(`${api}/production-tasks/${id}`)
  ).json();
  expect(task.status).toBe("physically_completed");
  expect(task.planned_quantity).toBe("1.000001");
  expect(task.notes).toBe("Nota conservada");
  const runs = await (
    await request.get(`${api}/production-tasks/${id}/runs`)
  ).json();
  expect(runs).toHaveLength(1);
  expect(runs[0].good_quantity).toBe("1.000001");
  expect(runs[0].parameters).toEqual({ speed: "25.000001" });
  expect(runs[0].started_at).toContain("2026-10-01T10:00:00");
  const consumptions = await (
    await request.get(
      `${api}/production-runs/${runs[0].id}/supply-consumptions`,
    )
  ).json();
  expect(consumptions[0].consumed).toBe("2.123456");
  const stock = await (
    await request.get(`${api}/product-variants/${variant.id}/stock`)
  ).json();
  expect(stock.physical_quantity).toBe("1.000001");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
test("dependencias entre componentes, ciclo rechazado y retiro explícito", async ({
  page,
  request,
}) => {
  const project = await seed(request, true);
  const a = await post(
    request,
    `/project-components/${project.components[0].id}/production-tasks`,
    {
      title: "Previa",
      task_type: "manual",
      planned_quantity: "1",
      planned_unit: "unit",
    },
  );
  const b = await post(
    request,
    `/project-components/${project.components[1].id}/production-tasks`,
    {
      title: "Posterior",
      task_type: "manual",
      planned_quantity: "1",
      planned_unit: "unit",
    },
  );
  await page.goto(`/task-edit/${b.id}`);
  await page
    .getByRole("combobox", { name: "Prerrequisito", exact: true })
    .selectOption(a.id);
  await page
    .getByRole("button", { name: "Agregar prerrequisito", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Retirar Previa", exact: true }),
  ).toBeVisible();
  await page.goto(`/task-edit/${a.id}`);
  await page
    .getByRole("combobox", { name: "Prerrequisito", exact: true })
    .selectOption(b.id);
  await page
    .getByRole("button", { name: "Agregar prerrequisito", exact: true })
    .click();
  await expect(
    page.getByRole("alert").filter({ hasText: /ciclo/i }),
  ).toBeVisible();
  page.on("dialog", (dialog) => dialog.accept());
  await page.goto(`/task-edit/${b.id}`);
  await page
    .getByRole("button", { name: "Retirar Previa", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Retirar Previa", exact: true }),
  ).toHaveCount(0);
  expect(
    await (
      await request.get(`${api}/production-tasks/${b.id}/dependencies`)
    ).json(),
  ).toEqual([]);
});
test("alta manual incierta no se duplica al recargar", async ({
  page,
  request,
}) => {
  const order = await seed(request);
  let posts = 0;
  await page.goto(`/production/tasks/new?order=${order.id}`);
  await page
    .getByLabel("Título de tarea", { exact: true })
    .fill("Alta incierta");
  await page.getByLabel("Confirmo la planificación de la tarea.").check();
  await page.route(
    `**/api/v1/orders/${order.id}/production-tasks`,
    async (route) => {
      posts++;
      await route.fetch();
      await route.abort("failed");
    },
  );
  await page
    .getByRole("button", { name: "Crear tarea manual", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "Revisar operación incierta" }),
  ).toBeVisible();
  page.on("dialog", (dialog) => dialog.accept());
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Crear tarea manual", exact: true }),
  ).toBeDisabled();
  expect(posts).toBe(1);
  expect(
    await (
      await request.get(`${api}/production-tasks?order_id=${order.id}`)
    ).json(),
  ).toHaveLength(1);
});

test("tarea histórica usa lifecycle legacy y no crea Runs", async ({
  page,
  request,
}) => {
  const order = await seed(request);
  const task = await post(request, `/orders/${order.id}/production-tasks`, {
    title: "Fixture legacy visual",
    task_type: "manual",
    planned_quantity: "1",
  });
  let status = "queued";
  const actions: string[] = [];
  await page.route(`**/api/v1/production-tasks/${task.id}`, (route) =>
    route.fulfill({ json: { ...task, execution_mode: "legacy", status } }),
  );
  for (const action of ["start", "pause", "resume", "finish"])
    await page.route(
      `**/api/v1/production-tasks/${task.id}/${action}`,
      (route) => {
        actions.push(action);
        status =
          action === "pause"
            ? "paused"
            : action === "finish"
              ? "physically_completed"
              : "in_progress";
        return route.fulfill({
          json: { ...task, execution_mode: "legacy", status },
        });
      },
    );
  await page.goto(`/production/tasks/${task.id}`);
  for (const label of [
    "Iniciar tarea histórica",
    "Pausar tarea histórica",
    "Reanudar tarea histórica",
    "Finalizar físicamente",
  ]) {
    await page
      .getByLabel("Confirmo el cambio de estado de la tarea histórica.")
      .check();
    await page.getByRole("button", { name: label, exact: true }).click();
    await expect(
      page.getByRole("button", { name: label, exact: true }),
    ).toHaveCount(0);
  }
  expect(actions).toEqual(["start", "pause", "resume", "finish"]);
  expect(
    await (await request.get(`${api}/production-tasks/${task.id}/runs`)).json(),
  ).toEqual([]);
});

test("edición incierta conserva borrador y permite revisar la planificación guardada", async ({
  page,
  request,
}) => {
  const order = await seed(request);
  const task = await post(request, `/orders/${order.id}/production-tasks`, {
    title: "Revisión de edición",
    task_type: "manual",
    planned_quantity: "1",
  });
  let patches = 0;
  await page.goto(`/task-edit/${task.id}`);
  await page
    .getByLabel("Notas operativas", { exact: true })
    .fill("Nota efectivamente guardada");
  await page
    .getByRole("button", { name: "Consultar registros actuales", exact: true })
    .click();
  await expect(
    page.getByLabel("Notas operativas", { exact: true }),
  ).toHaveValue("Nota efectivamente guardada");
  await page.getByLabel("Confirmo la planificación de la tarea.").check();
  await page.route(`**/api/v1/production-tasks/${task.id}`, async (route) => {
    if (route.request().method() === "PATCH") {
      patches++;
      await route.fetch();
      await route.abort("failed");
    } else await route.continue();
  });
  await page
    .getByRole("button", { name: "Guardar tarea", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "Revisar operación incierta" }),
  ).toBeVisible();
  await page.getByText("Planificación guardada", { exact: true }).click();
  await expect(
    page.locator("details").filter({ hasText: "Planificación guardada" }),
  ).toContainText("Nota efectivamente guardada");
  page.on("dialog", (dialog) => dialog.accept());
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Guardar tarea", exact: true }),
  ).toBeDisabled();
  expect(patches).toBe(1);
  expect(
    (await (await request.get(`${api}/production-tasks/${task.id}`)).json())
      .notes,
  ).toBe("Nota efectivamente guardada");
});
