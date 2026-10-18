import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
const api = process.env.RRII_E2E_API_BASE!;
test("Servicios: alta, edición, validación, preview y filtros en móvil", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  page.on("dialog", (dialog) => dialog.accept());
  await page.setViewportSize({ width: 360, height: 960 });
  const name = `Servicio UI ${Date.now()}`;
  await page.goto("/");
  await page.getByRole("button", { name: "Más", exact: true }).click();
  await page
    .getByRole("menuitem", { name: "Servicios reutilizables", exact: true })
    .click();
  await page
    .getByRole("link", { name: "Registrar servicio", exact: true })
    .click();
  await page.getByLabel("Nombre", { exact: true }).fill(name);
  await page
    .getByLabel("Plantilla de acción", { exact: true })
    .fill("Grabar {unknown}");
  await page
    .getByLabel("Confirmo los datos y el estado del servicio.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar servicio", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Sólo se admiten");
  await page
    .getByLabel("Plantilla de acción", { exact: true })
    .fill("Grabar {quantity} de {piece} con {design} para {product}");
  await page
    .getByLabel("Instrucciones", { exact: true })
    .fill("Verificar acabado");
  await page
    .getByRole("button", { name: "Guardar servicio", exact: true })
    .click();
  await expect(page).toHaveURL(/\/services\/[0-9a-f-]{36}$/);
  const id = page.url().split("/").pop();
  const preview = page.getByRole("region", {
    name: "Probar frase guardada",
    exact: true,
  });
  await preview
    .getByRole("button", { name: "Previsualizar frase", exact: true })
    .click();
  await expect(preview.getByRole("alert")).toContainText("Falta contexto");
  await preview.getByLabel("Pieza", { exact: true }).fill("{product}");
  await preview.getByLabel("Diseño", { exact: true }).fill("Logo");
  await preview.getByLabel("Producto", { exact: true }).fill("Caja");
  await preview
    .getByLabel("Cantidad (etiqueta)", { exact: true })
    .fill("2 unidades");
  await preview
    .getByRole("button", { name: "Previsualizar frase", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "Resultado de frase" }),
  ).toContainText("Grabar 2 unidades de {product} con Logo para Caja");
  const stored = await (
    await request.get(`${api}/service-definitions/${id}`)
  ).json();
  await preview.getByLabel("Producto", { exact: true }).fill("Otra caja");
  await expect(
    page.getByRole("region", { name: "Resultado de frase" }),
  ).toHaveCount(0);
  expect(
    await (await request.get(`${api}/service-definitions/${id}`)).json(),
  ).toEqual(stored);
  for (const value of [name + " editado", name]) {
    await page.getByLabel("Nombre", { exact: true }).fill(value);
    await page
      .getByLabel("Confirmo los datos y el estado del servicio.", {
        exact: true,
      })
      .check();
    await page
      .getByRole("button", { name: "Guardar servicio", exact: true })
      .click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(value);
  }
  await page.getByLabel("Plantilla de acción", { exact: true }).fill("");
  await page.getByLabel("Activo", { exact: true }).uncheck();
  await page
    .getByLabel("Confirmo los datos y el estado del servicio.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar servicio", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "Datos guardados" }),
  ).toContainText("Inactivo");
  expect(
    (await (await request.get(`${api}/service-definitions/${id}`)).json())
      .action_template,
  ).toBeNull();
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
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({ path: "test-results/services-mobile.png" });
  await page
    .getByRole("link", { name: "Servicios reutilizables", exact: true })
    .click();
  await page.getByLabel("Buscar servicio", { exact: true }).fill(name);
  await page
    .getByRole("combobox", { name: "Estado", exact: true })
    .selectOption("false");
  await page
    .getByRole("button", { name: "Aplicar filtros", exact: true })
    .click();
  await expect(page.getByRole("link", { name, exact: true })).toBeVisible();
});
test("Servicios: alta incierta no se reenvía; preview tardía se descarta", async ({
  page,
  request,
}) => {
  page.on("dialog", (dialog) => dialog.accept());
  const name = `Servicio incierto ${Date.now()}`;
  let writes = 0;
  await page.route("**/api/v1/service-definitions", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    writes++;
    const response = await route.fetch();
    expect(response.ok()).toBe(true);
    await route.abort();
  });
  await page.goto("/services/new");
  await page.getByLabel("Nombre", { exact: true }).fill(name);
  await page
    .getByLabel("Plantilla de acción", { exact: true })
    .fill("Grabar {piece}");
  await page
    .getByLabel("Confirmo los datos y el estado del servicio.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar servicio", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "Revisar operación incierta" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Guardar servicio", exact: true }),
  ).toBeDisabled();
  expect(writes).toBe(1);
  await page.getByRole("link", { name, exact: true }).click();
  await expect(page).toHaveURL(/\/services\/[0-9a-f-]{36}$/);
  const id = page.url().split("/").pop();
  const rows = await (
    await request.get(
      `${api}/service-definitions?search=${encodeURIComponent(name)}`,
    )
  ).json();
  expect(rows).toHaveLength(1);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let started!: () => void;
  const received = new Promise<void>((resolve) => {
    started = resolve;
  });
  await page.route(
    `**/api/v1/service-definitions/${id}/action-preview`,
    async (route) => {
      const response = await route.fetch();
      started();
      await gate;
      await route.fulfill({ response });
    },
  );
  await page.getByLabel("Pieza", { exact: true }).fill("Anterior");
  await page
    .getByRole("button", { name: "Previsualizar frase", exact: true })
    .click();
  await received;
  await page.getByLabel("Pieza", { exact: true }).fill("Nueva");
  const completed = page.waitForResponse((response) =>
    response.url().endsWith("/action-preview"),
  );
  release();
  await (await completed).finished();
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await expect(
    page.getByRole("region", { name: "Resultado de frase" }),
  ).toHaveCount(0);
  await page.unroute(`**/api/v1/service-definitions/${id}/action-preview`);
  await page
    .getByRole("button", { name: "Previsualizar frase", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "Resultado de frase" }),
  ).toContainText("Grabar Nueva");
});
