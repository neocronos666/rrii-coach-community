import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
const api = process.env.RRII_E2E_API_BASE!;
test("Datos de Assets: metadata completa, URL inválida, null e historia intacta en móvil", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  page.on("dialog", (dialog) => dialog.accept());
  await page.setViewportSize({ width: 360, height: 960 });
  const response = await request.post(`${api}/assets`, {
    data: { name: `Datos UI ${Date.now()}` },
  });
  expect(response.ok()).toBe(true);
  const asset = await response.json();
  const familyResponse = await request.post(`${api}/asset-families`, {
    data: { name: `Familia metadata ${Date.now()}` },
  });
  expect(familyResponse.ok()).toBe(true);
  const family = await familyResponse.json();
  const upload = await request.post(
    `${api}/assets/${asset.id}/revisions/${asset.current_revision_id}/files?filename=original.txt&role=documentation`,
    {
      headers: { "Content-Type": "application/octet-stream" },
      data: Buffer.from("historia intacta"),
    },
  );
  expect(upload.ok()).toBe(true);
  const files = await (
    await request.get(
      `${api}/assets/${asset.id}/revisions/${asset.current_revision_id}/files`,
    )
  ).json();
  const revisions = await (
    await request.get(`${api}/assets/${asset.id}/revisions`)
  ).json();
  await page.goto(`/assets/${asset.id}`);
  await page
    .getByRole("link", { name: "Editar datos del Asset", exact: true })
    .click();
  await page
    .getByLabel("Descripción", { exact: true })
    .fill("Descripción completa");
  await page.getByLabel("Autor", { exact: true }).fill("Autor de prueba");
  await page.getByLabel("Origen", { exact: true }).fill("Catálogo externo");
  await page.getByLabel("Licencia", { exact: true }).fill("Licencia declarada");
  await page
    .getByLabel("Notas de uso", { exact: true })
    .fill("Revisar condiciones de uso");
  await page.getByLabel("Recurso de terceros", { exact: true }).check();
  await page
    .getByRole("combobox", { name: "Familia de diseño", exact: true })
    .selectOption(family.id);
  await page.getByLabel("URL de origen", { exact: true }).fill("no es una URL");
  await page
    .getByLabel("Confirmo los datos y el estado del Asset.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar datos del Asset", exact: true })
    .click();
  await expect(page.getByRole("alert")).toBeVisible();
  await page
    .getByLabel("URL de origen", { exact: true })
    .fill("https://example.org/design");
  await page
    .getByRole("button", { name: "Guardar datos del Asset", exact: true })
    .click();
  await expect(
    page.getByText("Operación registrada.", { exact: true }),
  ).toBeVisible();
  expect(
    await (await request.get(`${api}/assets/${asset.id}`)).json(),
  ).toMatchObject({
    description: "Descripción completa",
    author: "Autor de prueba",
    origin: "Catálogo externo",
    license: "Licencia declarada",
    source_url: "https://example.org/design",
    third_party: true,
    family_id: family.id,
    current_revision_id: asset.current_revision_id,
  });
  for (const name of [asset.name + " cambiado", asset.name]) {
    await page.getByLabel("Nombre", { exact: true }).fill(name);
    await page
      .getByLabel("Confirmo los datos y el estado del Asset.", { exact: true })
      .check();
    await page
      .getByRole("button", { name: "Guardar datos del Asset", exact: true })
      .click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      `Datos · ${name}`,
    );
  }
  await page.getByLabel("Autor", { exact: true }).fill("");
  await page.getByLabel("URL de origen", { exact: true }).fill("");
  await page.getByLabel("Archivado", { exact: true }).check();
  await page
    .getByLabel("Confirmo los datos y el estado del Asset.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar datos del Asset", exact: true })
    .click();
  await expect
    .poll(
      async () =>
        (await (await request.get(`${api}/assets/${asset.id}`)).json())
          .archived,
    )
    .toBe(true);
  expect(
    await (await request.get(`${api}/assets/${asset.id}`)).json(),
  ).toMatchObject({ author: null, source_url: null });
  expect(
    await (await request.get(`${api}/assets/${asset.id}/revisions`)).json(),
  ).toEqual(revisions);
  expect(
    await (
      await request.get(
        `${api}/assets/${asset.id}/revisions/${asset.current_revision_id}/files`,
      )
    ).json(),
  ).toEqual(files);
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
  await page.screenshot({ path: "test-results/asset-details-mobile.png" });
});
test("Categorías: alta, renombrado, protección y eliminación incierta con reasignación", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  page.on("dialog", (dialog) => dialog.accept());
  const name = `Categoría UI ${Date.now()}`;
  await page.goto("/assets");
  await page
    .getByRole("link", { name: "Administrar categorías", exact: true })
    .click();
  await page
    .getByRole("link", { name: "Crear categoría", exact: true })
    .click();
  await page.getByLabel("Nombre", { exact: true }).fill(name);
  await page
    .getByLabel("Confirmo el nombre de la categoría.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar categoría", exact: true })
    .click();
  await expect(page).toHaveURL(/\/asset-categories\/[0-9a-f-]{36}$/);
  const id = page.url().split("/").pop();
  await page.getByLabel("Nombre", { exact: true }).fill(name + " renombrada");
  await page
    .getByLabel("Confirmo el nombre de la categoría.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar categoría", exact: true })
    .click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    name + " renombrada",
  );
  const created = await request.post(`${api}/assets`, {
    data: { name: `Reasignar ${Date.now()}`, category_id: id },
  });
  expect(created.ok()).toBe(true);
  const asset = await created.json();
  let writes = 0;
  await page.route(`**/api/v1/asset-categories/${id}`, async (route) => {
    if (route.request().method() !== "DELETE") return route.continue();
    writes++;
    const response = await route.fetch();
    expect(response.status()).toBe(204);
    await route.abort();
  });
  await page
    .getByRole("button", { name: "Eliminar categoría", exact: true })
    .click();
  const review = page.getByRole("region", {
    name: "Revisar operación incierta",
  });
  await expect(review).toBeVisible();
  await expect(
    page.getByText(
      "La categoría ya no aparece en los registros actuales. Revisá el listado antes de realizar otra operación.",
      { exact: true },
    ),
  ).toBeVisible();
  await page.reload();
  await expect(review).toBeVisible();
  expect(writes).toBe(1);
  const categories = await (
    await request.get(`${api}/asset-categories`)
  ).json();
  const system = categories.find(
    (row: { system_key: string | null }) => row.system_key,
  );
  expect(system).toBeTruthy();
  expect(categories.some((row: { id: string }) => row.id === id)).toBe(false);
  expect(
    await (await request.get(`${api}/assets/${asset.id}`)).json(),
  ).toMatchObject({
    category_id: system.id,
    current_revision_id: asset.current_revision_id,
  });
  await page.goto(`/asset-categories/${system.id}`);
  await expect(
    page.getByRole("button", { name: "Guardar categoría", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Eliminar categoría", exact: true }),
  ).toHaveCount(0);
});
test("Metadata: respuesta perdida no reenvía y consulta conserva borrador", async ({
  page,
  request,
}) => {
  page.on("dialog", (dialog) => dialog.accept());
  const created = await request.post(`${api}/assets`, {
    data: { name: `Metadata incierta ${Date.now()}` },
  });
  expect(created.ok()).toBe(true);
  const asset = await created.json();
  let writes = 0;
  await page.goto(`/asset-details/${asset.id}`);
  await page.getByLabel("Autor", { exact: true }).fill("Autor local");
  await page
    .getByRole("button", { name: "Consultar datos guardados", exact: true })
    .click();
  await expect(page.getByLabel("Autor", { exact: true })).toHaveValue(
    "Autor local",
  );
  await page.route(`**/api/v1/assets/${asset.id}`, async (route) => {
    if (route.request().method() !== "PATCH") return route.continue();
    writes++;
    const response = await route.fetch();
    expect(response.ok()).toBe(true);
    await route.abort();
  });
  await page
    .getByLabel("Confirmo los datos y el estado del Asset.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar datos del Asset", exact: true })
    .click();
  const review = page.getByRole("region", {
    name: "Revisar operación incierta",
  });
  await expect(review).toBeVisible();
  await page.reload();
  await expect(review).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Guardar datos del Asset", exact: true }),
  ).toBeDisabled();
  await expect(page.getByLabel("Autor", { exact: true })).toHaveValue(
    "Autor local",
  );
  expect(writes).toBe(1);
});
