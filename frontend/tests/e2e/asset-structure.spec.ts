import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
const api = process.env.RRII_E2E_API_BASE!;
async function asset(request: APIRequestContext, name: string) {
  const r = await request.post(`${api}/assets`, {
    data: { name: `${name} ${Date.now()}` },
  });
  expect(r.ok(), await r.text()).toBe(true);
  return r.json();
}
async function publish(page: Page) {
  await page
    .getByLabel(
      "Confirmo publicar la lista completa de componentes en una revisión nueva.",
      { exact: true },
    )
    .check();
  await page
    .getByRole("button", { name: "Publicar composición", exact: true })
    .click();
}
async function component(
  page: Page,
  child: string,
  revision: string,
  quantity = "1",
) {
  await page
    .getByRole("button", { name: "Agregar componente", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Asset hijo", exact: true })
    .selectOption(child);
  await page
    .getByRole("combobox", { name: "Revisión hija", exact: true })
    .selectOption(revision);
  await page
    .getByLabel("Cantidad del componente", { exact: true })
    .fill(quantity);
}
test("Estructura: familias y compatibilidades simétricas en móvil", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  page.on("dialog", (dialog) => dialog.accept());
  await page.setViewportSize({ width: 360, height: 960 });
  const name = `Familia UI ${Date.now()}`;
  await page.goto("/");
  await page.getByRole("button", { name: "Más", exact: true }).click();
  await page
    .getByRole("menuitem", { name: "Familias de diseño", exact: true })
    .click();
  await page.getByRole("link", { name: "Crear familia", exact: true }).click();
  await page.getByLabel("Nombre", { exact: true }).fill(name);
  await page
    .getByLabel("Descripción", { exact: true })
    .fill("Descripción inicial");
  await page
    .getByLabel("Confirmo los datos de la familia.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar familia", exact: true })
    .click();
  await expect(page).toHaveURL(/\/families\/[0-9a-f-]{36}$/);
  const family = page.url().split("/").pop();
  for (const title of [name + " editada", name]) {
    await page.getByLabel("Nombre", { exact: true }).fill(title);
    await page.getByLabel("Descripción", { exact: true }).fill("");
    await page
      .getByLabel("Confirmo los datos de la familia.", { exact: true })
      .check();
    await page
      .getByRole("button", { name: "Guardar familia", exact: true })
      .click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(title);
  }
  expect(
    (await (await request.get(`${api}/asset-families/${family}`)).json())
      .description,
  ).toBeNull();
  const parent = await asset(request, "Padre relaciones"),
    other = await asset(request, "Compatible");
  await page.goto(`/assets/${parent.id}`);
  await page
    .getByRole("link", {
      name: "Familia, compatibilidades y composición",
      exact: true,
    })
    .click();
  await expect(page).toHaveURL(/\/asset-structure\//);
  await page
    .getByRole("combobox", { name: "Familia de diseño", exact: true })
    .selectOption(family!);
  await page
    .getByLabel("Confirmo el cambio de relación indicado.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar familia del Asset", exact: true })
    .click();
  await expect
    .poll(
      async () =>
        (await (await request.get(`${api}/assets/${parent.id}`)).json())
          .family_id,
    )
    .toBe(family);
  await page
    .getByRole("combobox", { name: "Asset compatible", exact: true })
    .selectOption(other.id);
  await page
    .getByLabel("Confirmo el cambio de relación indicado.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Registrar compatibilidad", exact: true })
    .click();
  await expect(
    page.getByRole("button", {
      name: `Retirar compatibilidad · ${other.name}`,
      exact: true,
    }),
  ).toBeVisible();
  expect(
    (
      await (
        await request.get(`${api}/assets/${other.id}/compatibilities`)
      ).json()
    ).items.map((r: { id: string }) => r.id),
  ).toContain(parent.id);
  await page
    .getByRole("button", {
      name: `Retirar compatibilidad · ${other.name}`,
      exact: true,
    })
    .click();
  await expect(
    page.getByText("Sin compatibilidades positivas registradas.", {
      exact: true,
    }),
  ).toBeVisible();
  expect(
    (
      await (
        await request.get(`${api}/assets/${other.id}/compatibilities`)
      ).json()
    ).items,
  ).toHaveLength(0);
  await page
    .getByRole("combobox", { name: "Familia de diseño", exact: true })
    .selectOption({ label: "Sin familia" });
  await page
    .getByLabel("Confirmo el cambio de relación indicado.", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Guardar familia del Asset", exact: true })
    .click();
  await expect
    .poll(
      async () =>
        (await (await request.get(`${api}/assets/${parent.id}`)).json())
          .family_id,
    )
    .toBeNull();
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
  await page.screenshot({ path: "test-results/asset-structure-mobile.png" });
});
test("Estructura: publicación conserva archivos, adopción explícita, historia y ciclos", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  page.on("dialog", (dialog) => dialog.accept());
  const parent = await asset(request, "Ensamble"),
    child = await asset(request, "Hijo");
  const upload = await request.post(
    `${api}/assets/${parent.id}/revisions/${parent.current_revision_id}/files?filename=base.txt&role=documentation`,
    {
      headers: { "Content-Type": "application/octet-stream" },
      data: Buffer.from("archivo conservado"),
    },
  );
  expect(upload.ok(), await upload.text()).toBe(true);
  await page.goto(
    `/asset-structure/${parent.id}?revision=${parent.current_revision_id}`,
  );
  await component(page, child.id, child.current_revision_id, "2.123456");
  await publish(page);
  await expect(page).not.toHaveURL(new RegExp(parent.current_revision_id));
  const revision2 = (
    await (await request.get(`${api}/assets/${parent.id}`)).json()
  ).current_revision_id;
  const composition = await (
    await request.get(
      `${api}/assets/${parent.id}/revisions/${revision2}/composition`,
    )
  ).json();
  expect(composition).toHaveLength(1);
  expect(composition[0]).toMatchObject({
    child_asset_id: child.id,
    child_revision_id: child.current_revision_id,
    quantity: "2.123456",
  });
  expect(
    await (
      await request.get(
        `${api}/assets/${parent.id}/revisions/${parent.current_revision_id}/composition`,
      )
    ).json(),
  ).toEqual([]);
  expect(
    (
      await (
        await request.get(
          `${api}/assets/${parent.id}/revisions/${revision2}/files`,
        )
      ).json()
    ).map((r: { filename: string }) => r.filename),
  ).toEqual(["base.txt"]);
  const childNext = await request.post(`${api}/assets/${child.id}/revisions`, {
    data: { note: "Nueva hija" },
  });
  expect(childNext.ok()).toBe(true);
  const next = await childNext.json();
  expect(
    (
      await request.patch(`${api}/assets/${child.id}`, {
        data: { archived: true },
      })
    ).ok(),
  ).toBe(true);
  await page
    .getByRole("button", { name: "Consultar registros actuales", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: `Adoptar revisión actual · ${child.name}`,
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("combobox", { name: "Revisión hija", exact: true }),
  ).toHaveValue(next.id);
  expect(
    (
      await (
        await request.get(
          `${api}/assets/${parent.id}/revisions/${revision2}/composition`,
        )
      ).json()
    )[0].child_revision_id,
  ).toBe(child.current_revision_id);
  await publish(page);
  await expect(page).not.toHaveURL(new RegExp(revision2));
  const revision3 = (
    await (await request.get(`${api}/assets/${parent.id}`)).json()
  ).current_revision_id;
  expect(
    (
      await (
        await request.get(
          `${api}/assets/${parent.id}/revisions/${revision3}/composition`,
        )
      ).json()
    )[0].child_revision_id,
  ).toBe(next.id);
  await page.goto(`/asset-structure/${parent.id}?revision=${revision2}`);
  await expect(
    page.getByRole("button", { name: "Publicar composición", exact: true }),
  ).toBeDisabled();
  await page.goto(`/asset-structure/${child.id}?revision=${next.id}`);
  await component(page, parent.id, revision3);
  await publish(page);
  await expect(page.getByRole("alert")).toContainText("sin ciclos");
  await expect(
    page.getByRole("combobox", { name: "Asset hijo", exact: true }),
  ).toHaveValue(parent.id);
  await page.goto(`/asset-structure/${parent.id}?revision=${revision3}`);
  await page
    .getByRole("button", { name: "Quitar componente 1", exact: true })
    .click();
  await publish(page);
  await expect(page).not.toHaveURL(new RegExp(revision3));
  const revision4 = (
    await (await request.get(`${api}/assets/${parent.id}`)).json()
  ).current_revision_id;
  expect(
    await (
      await request.get(
        `${api}/assets/${parent.id}/revisions/${revision4}/composition`,
      )
    ).json(),
  ).toEqual([]);
  expect(
    await (
      await request.get(
        `${api}/assets/${parent.id}/revisions/${revision3}/composition`,
      )
    ).json(),
  ).toHaveLength(1);
});
test("Estructura: conflicto de base y publicación incierta sin duplicación", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  page.on("dialog", (dialog) => dialog.accept());
  const parent = await asset(request, "Incierta"),
    child = await asset(request, "Componente");
  await page.goto(
    `/asset-structure/${parent.id}?revision=${parent.current_revision_id}`,
  );
  await component(page, child.id, child.current_revision_id);
  const external = await request.post(`${api}/assets/${parent.id}/revisions`, {
    data: { note: "Externa" },
  });
  expect(external.ok()).toBe(true);
  const newer = await external.json();
  await publish(page);
  await expect(page.getByRole("alert")).toContainText("revisión actual cambió");
  await expect(
    page.getByRole("button", { name: "Publicar composición", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("link", { name: "Abrir revisión actual", exact: true })
    .click();
  await expect(page).toHaveURL(new RegExp(newer.id));
  await component(page, child.id, child.current_revision_id);
  let writes = 0;
  await page.route(
    `**/api/v1/assets/${parent.id}/composition-revisions`,
    async (route) => {
      writes++;
      const response = await route.fetch();
      expect(response.ok(), await response.text()).toBe(true);
      await route.abort();
    },
  );
  await publish(page);
  const review = page.getByRole("region", {
    name: "Revisar operación incierta",
  });
  await expect(review).toBeVisible();
  await page.reload();
  await expect(review).toBeVisible();
  expect(writes).toBe(1);
  expect(
    await (await request.get(`${api}/assets/${parent.id}/revisions`)).json(),
  ).toHaveLength(3);
  await page
    .getByRole("link", { name: "Abrir revisión actual", exact: true })
    .click();
  await expect(review).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Publicar composición", exact: true }),
  ).toBeDisabled();
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
  await expect(
    page.getByRole("button", { name: "Publicar composición", exact: true }),
  ).toBeEnabled();
  expect(writes).toBe(1);
});
