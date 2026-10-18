import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
const api = process.env.RRII_E2E_API_BASE!;
test("Opciones: catálogo global, vínculos, conflictos y actividad independiente en móvil", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  page.on("dialog", (dialog) => dialog.accept());
  await page.setViewportSize({ width: 360, height: 960 });
  const tag = Date.now(),
    name = `Característica UI ${tag}`;
  const familyResponse = await request.post(`${api}/asset-families`, {
    data: { name: `Familia UI ${tag}` },
  });
  expect(familyResponse.ok()).toBe(true);
  const family = await familyResponse.json();
  const supplyResponse = await request.post(`${api}/supplies`, {
    data: { name: `Insumo UI ${tag}`, category: "material", base_unit: "g" },
  });
  expect(supplyResponse.ok()).toBe(true);
  const supply = await supplyResponse.json();
  await page.goto("/");
  await page.getByRole("button", { name: "Más", exact: true }).click();
  await page
    .getByRole("menuitem", { name: "Opciones y valores", exact: true })
    .click();
  await page
    .getByRole("link", { name: "Crear característica", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Crear característica", exact: true, level: 1 }),
  ).toBeVisible();
  await page.getByLabel("Nombre", { exact: true }).fill(name);
  await page
    .getByLabel("Descripción", { exact: true })
    .fill("Descripción global");
  await page
    .getByLabel("Confirmo los datos y el estado del catálogo.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar cambios", exact: true })
    .click();
  await expect(page).toHaveURL(/\/options\/[0-9a-f-]{36}$/);
  const definition = page.url().split("/").pop()!;
  await page.getByRole("link", { name: "Crear valor", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Crear valor", exact: true, level: 1 }),
  ).toBeVisible();
  await page.getByLabel("Nombre", { exact: true }).fill("Valor enlazado");
  await page
    .getByRole("combobox", { name: "Familia de diseño", exact: true })
    .selectOption(family.id);
  await page
    .getByRole("combobox", { name: "Insumo", exact: true })
    .selectOption(supply.id);
  await page
    .getByLabel("Confirmo los datos y el estado del catálogo.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar cambios", exact: true })
    .click();
  await expect(page).toHaveURL(/\/values\/[0-9a-f-]{36}$/);
  const value = page.url().split("/").pop()!;
  const endpoint = `${api}/option-definitions/${definition}/values/${value}`;
  expect(await (await request.get(endpoint)).json()).toMatchObject({
    family_id: family.id,
    supply_id: supply.id,
    active: true,
  });
  // El PATCH de nombre no reenvía el vínculo a un insumo que se desactivó.
  expect(
    (
      await request.patch(`${api}/supplies/${supply.id}`, {
        data: { active: false },
      })
    ).ok(),
  ).toBe(true);
  await page
    .getByRole("button", { name: "Actualizar familias e insumos", exact: true })
    .click();
  for (const title of ["Valor editado", "Valor enlazado"]) {
    await page.getByLabel("Nombre", { exact: true }).fill(title);
    await page
      .getByLabel("Confirmo los datos y el estado del catálogo.", {
        exact: true,
      })
      .check();
    await page
      .getByRole("button", { name: "Guardar cambios", exact: true })
      .click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(title);
  }
  await page
    .getByRole("combobox", { name: "Familia de diseño", exact: true })
    .selectOption({ label: "Sin vínculo" });
  await page
    .getByRole("combobox", { name: "Insumo", exact: true })
    .selectOption({ label: "Sin vínculo" });
  await page
    .getByLabel("Confirmo los datos y el estado del catálogo.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar cambios", exact: true })
    .click();
  await expect
    .poll(async () => (await (await request.get(endpoint)).json()).supply_id)
    .toBeNull();
  expect((await (await request.get(endpoint)).json()).family_id).toBeNull();
  await page
    .getByRole("combobox", { name: "Insumo", exact: true })
    .selectOption(supply.id);
  await page
    .getByLabel("Confirmo los datos y el estado del catálogo.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar cambios", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("inactivo");
  await expect(
    page.getByRole("combobox", { name: "Insumo", exact: true }),
  ).toHaveValue(supply.id);
  await page
    .getByRole("combobox", { name: "Insumo", exact: true })
    .selectOption({ label: "Sin vínculo" });
  await page
    .getByRole("link", { name: "Volver a la característica", exact: true })
    .click();
  await page.getByLabel("Activo", { exact: true }).uncheck();
  await page.getByLabel("Descripción", { exact: true }).fill("");
  await page
    .getByLabel("Confirmo los datos y el estado del catálogo.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar cambios", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "Datos guardados" }),
  ).toContainText("Inactivo");
  expect((await (await request.get(endpoint)).json()).active).toBe(true);
  expect(
    (
      await (
        await request.get(`${api}/option-definitions/${definition}`)
      ).json()
    ).description,
  ).toBeNull();
  const list = page.getByRole("region", {
    name: "Valores de la característica",
    exact: true,
  });
  await list
    .getByLabel("Buscar por nombre", { exact: true })
    .fill("Valor enlazado");
  await list
    .getByRole("button", { name: "Aplicar filtros", exact: true })
    .click();
  await expect(
    list.getByRole("link", { name: "Valor enlazado", exact: true }),
  ).toBeVisible();
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
  await page.screenshot({ path: "test-results/options-mobile.png" });
});
test("Opciones: alta y edición inciertas no se reenvían; pertenencia inválida no habilita editor", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  page.on("dialog", (dialog) => dialog.accept());
  const response = await request.post(`${api}/option-definitions`, {
    data: { name: `Padre incierto ${Date.now()}` },
  });
  expect(response.ok()).toBe(true);
  const parent = await response.json();
  const name = `Valor incierto ${Date.now()}`;
  let creates = 0,
    updates = 0;
  await page.route(
    `**/api/v1/option-definitions/${parent.id}/values`,
    async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      creates++;
      const saved = await route.fetch();
      expect(saved.ok()).toBe(true);
      await route.abort();
    },
  );
  await page.goto(`/options/${parent.id}/values/new`);
  await page.getByLabel("Nombre", { exact: true }).fill(name);
  await page
    .getByLabel("Confirmo los datos y el estado del catálogo.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar cambios", exact: true })
    .click();
  const review = page.getByRole("region", {
    name: "Revisar operación incierta",
  });
  await expect(review).toBeVisible();
  await page.reload();
  await expect(review).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Guardar cambios", exact: true }),
  ).toBeDisabled();
  expect(creates).toBe(1);
  await page.getByRole("link", { name, exact: true }).click();
  await expect(page).toHaveURL(/\/values\/[0-9a-f-]{36}$/);
  const id = page.url().split("/").pop();
  await page.route(
    `**/api/v1/option-definitions/${parent.id}/values/${id}`,
    async (route) => {
      if (route.request().method() !== "PATCH") return route.continue();
      updates++;
      const saved = await route.fetch();
      expect(saved.ok()).toBe(true);
      await route.abort();
    },
  );
  await page
    .getByLabel("Descripción", { exact: true })
    .fill("Edición confirmada en servidor");
  await page
    .getByLabel("Confirmo los datos y el estado del catálogo.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar cambios", exact: true })
    .click();
  await expect(review).toBeVisible();
  await page.reload();
  await expect(review).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Datos guardados" }),
  ).toContainText("Edición confirmada en servidor");
  expect(updates).toBe(1);
  const other = await (
    await request.post(`${api}/option-definitions`, {
      data: { name: `Otro padre ${Date.now()}` },
    })
  ).json();
  await page.goto(`/options/${other.id}/values/${id}`);
  await expect(page.getByRole("alert")).toContainText("No existe la opción");
  await expect(
    page.getByRole("button", { name: "Guardar cambios", exact: true }),
  ).toHaveCount(0);
});
