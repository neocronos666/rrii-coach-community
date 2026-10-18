import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
const api = process.env.RRII_E2E_API_BASE!;
test("Máquinas: alta, edición, filtros, precisión y respuesta perdida en móvil", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  await page.setViewportSize({ width: 360, height: 960 });
  page.on("dialog", (dialog) => dialog.accept());
  const name = `Máquina UI ${Date.now()}`;
  let creates = 0;
  await page.route("**/api/v1/machines", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    creates++;
    const response = await route.fetch();
    expect(response.ok()).toBe(true);
    await route.abort();
  });
  await page.goto("/machines/new");
  await page.getByLabel("Nombre", { exact: true }).fill(name);
  await page
    .getByRole("combobox", { name: "Tipo", exact: true })
    .selectOption("laser");
  await page.getByLabel("Activa", { exact: true }).uncheck();
  await page
    .getByLabel("Precio de compra", { exact: true })
    .fill("123456.7891");
  await page.getByLabel("Fecha de compra", { exact: true }).fill("2026-10-14");
  await page
    .getByLabel("Confirmo los datos y el estado de la máquina.", {
      exact: true,
    })
    .check();
  await page
    .getByRole("button", { name: "Guardar máquina", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "Revisar operación incierta" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Guardar máquina", exact: true }),
  ).toBeDisabled();
  expect(creates).toBe(1);
  await page.getByRole("link", { name, exact: true }).click();
  const records = await (await request.get(`${api}/machines`)).json();
  const found = records.filter((row: { name: string }) => row.name === name);
  expect(found).toHaveLength(1);
  const id = found[0].id;
  expect(found[0].purchase_price).toBe("123456.7891");
  expect(found[0].purchase_date).toBe("2026-10-14");
  await expect(
    page.getByRole("region", { name: "Datos guardados" }),
  ).toContainText("Desconocido");
  for (const value of [name + " editada", name]) {
    await page.getByLabel("Nombre", { exact: true }).fill(value);
    await page
      .getByLabel("Confirmo los datos y el estado de la máquina.", {
        exact: true,
      })
      .check();
    await page
      .getByRole("button", { name: "Guardar máquina", exact: true })
      .click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(value);
  }
  await page.getByLabel("Precio de compra", { exact: true }).fill("");
  await page
    .getByLabel("Confirmo los datos y el estado de la máquina.", {
      exact: true,
    })
    .check();
  await page
    .getByRole("button", { name: "Guardar máquina", exact: true })
    .click();
  await expect
    .poll(
      async () =>
        (await (await request.get(`${api}/machines/${id}`)).json())
          .purchase_price,
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
  await page.screenshot({ path: "test-results/machines-mobile.png" });
  await page
    .getByRole("link", { name: "Ver producción de esta máquina", exact: true })
    .click();
  await expect(page).toHaveURL(new RegExp(`machine=${id}`));
  await expect(
    page.getByRole("combobox", { name: "Máquina", exact: true }),
  ).toHaveValue(id);
  await page.goto("/machines");
  await page
    .getByRole("combobox", { name: "Estado", exact: true })
    .selectOption("false");
  await page
    .getByRole("combobox", { name: "Tipo", exact: true })
    .selectOption("laser");
  await expect(page.getByRole("link", { name, exact: true })).toBeVisible();
  await page
    .getByRole("combobox", { name: "Estado", exact: true })
    .selectOption("true");
  await expect(page.getByRole("link", { name, exact: true })).toHaveCount(0);
});
test("Máquinas: límite de activas, desactivar y reactivar con error conservado", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const original = await (
    await request.get(`${api}/machines?active=true`)
  ).json();
  const fixtures: string[] = [];
  try {
    for (let n = original.length; n < 2; n++) {
      const response = await request.post(`${api}/machines`, {
        data: {
          name: `Activa E2E ${Date.now()} ${n}`,
          machine_type: "other",
          active: true,
        },
      });
      expect(response.ok()).toBe(true);
      fixtures.push((await response.json()).id);
    }
    await page.goto("/machines/new");
    await page
      .getByLabel("Nombre", { exact: true })
      .fill(`Límite UI ${Date.now()}`);
    await page
      .getByLabel("Confirmo los datos y el estado de la máquina.", {
        exact: true,
      })
      .check();
    await page
      .getByRole("button", { name: "Guardar máquina", exact: true })
      .click();
    await expect(page.getByRole("alert")).toContainText("dos máquinas activas");
    await page.getByLabel("Activa", { exact: true }).uncheck();
    await page
      .getByRole("button", { name: "Guardar máquina", exact: true })
      .click();
    await expect(page).toHaveURL(/\/machines\/[0-9a-f-]{36}$/);
    const id = page.url().split("/").pop()!;
    fixtures.push(id);
    await page.getByLabel("Activa", { exact: true }).check();
    await page
      .getByLabel("Confirmo los datos y el estado de la máquina.", {
        exact: true,
      })
      .check();
    await page
      .getByRole("button", { name: "Guardar máquina", exact: true })
      .click();
    await expect(page.getByRole("alert")).toContainText("dos máquinas activas");
    // Desactivar sólo una fixture propia o preservar/restaurar una activa previa.
    const released = fixtures.find((value) => value !== id) ?? original[0].id;
    expect(
      (
        await request.patch(`${api}/machines/${released}`, {
          data: { active: false },
        })
      ).ok(),
    ).toBe(true);
    await page
      .getByRole("button", { name: "Guardar máquina", exact: true })
      .click();
    await expect(
      page.getByRole("region", { name: "Datos guardados" }),
    ).toContainText("Activa");
    await page.getByLabel("Activa", { exact: true }).uncheck();
    await page
      .getByLabel("Confirmo los datos y el estado de la máquina.", {
        exact: true,
      })
      .check();
    await page
      .getByRole("button", { name: "Guardar máquina", exact: true })
      .click();
    await expect(
      page.getByRole("region", { name: "Datos guardados" }),
    ).toContainText("Inactiva");
  } finally {
    for (const id of fixtures)
      expect(
        (
          await request.patch(`${api}/machines/${id}`, {
            data: { active: false },
          })
        ).ok(),
      ).toBe(true);
    for (const row of original)
      expect(
        (
          await request.patch(`${api}/machines/${row.id}`, {
            data: { active: true },
          })
        ).ok(),
      ).toBe(true);
  }
});

test("Máquinas: PATCH incierto se consulta sin reenvío y preserva el formulario", async ({ page, request }) => {
  const response = await request.post(`${api}/machines`, { data: { name: `Edición incierta ${Date.now()}`, machine_type: "other", active: false } });
  expect(response.ok()).toBe(true);
  const machine = await response.json();
  let writes = 0;
  await page.route(`**/api/v1/machines/${machine.id}`, async route => {
    if (route.request().method() !== "PATCH") return route.continue();
    writes++;
    const saved = await route.fetch(); expect(saved.ok()).toBe(true);
    await route.abort();
  });
  page.on("dialog", dialog => dialog.accept());
  await page.goto(`/machines/${machine.id}`);
  await page.getByLabel("Notas", { exact: true }).fill("Revisión documentada");
  await page.getByLabel("Confirmo los datos y el estado de la máquina.", { exact: true }).check();
  await page.getByRole("button", { name: "Guardar máquina", exact: true }).click();
  const review = page.getByRole("region", { name: "Revisar operación incierta" });
  await expect(review).toBeVisible();
  await expect(page.getByLabel("Notas", { exact: true })).toHaveValue("Revisión documentada");
  await page.reload();
  await expect(review).toBeVisible();
  await expect(page.getByRole("region", { name: "Datos guardados" })).toContainText("Revisión documentada");
  await review.getByRole("button", { name: "Consultar registros actuales", exact: true }).click();
  await review.getByLabel("Ya revisé los registros y el resultado de la operación.", { exact: true }).check();
  await review.getByRole("button", { name: "Habilitar nueva operación", exact: true }).click();
  await expect(page.getByRole("button", { name: "Guardar máquina", exact: true })).toBeEnabled();
  expect(writes).toBe(1);
});
