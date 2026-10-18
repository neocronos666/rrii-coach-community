import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
const api = process.env.RRII_E2E_API_BASE!;
test("Instalación: datos completos, validación, conflicto y móvil", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const original = await (await request.get(`${api}/settings`)).json();
  const baseline = {
    ...original,
    business_name: "Instalación E2E",
    deposit_policy: "none",
    deposit_type: null,
    deposit_value: null,
    training_hour_rate: "123.4567",
    default_markup_percentage: "32.1234",
  };
  expect((await request.put(`${api}/settings`, { data: baseline })).ok()).toBe(
    true,
  );
  try {
    page.on("dialog", (dialog) => dialog.accept());
    await page.setViewportSize({ width: 360, height: 960 });
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("data-navigation", "bottom");
    await page.getByRole("button", { name: "Más", exact: true }).filter({ visible: true }).click();
    await page.getByRole("menuitem", { name: "Configuración de instalación", exact: true }).click();
    await expect(page).toHaveURL(/\/settings$/);
    await expect(
      page.getByLabel("Capacitación por hora", { exact: true }),
    ).toHaveValue("123.4567");
    await page
      .getByLabel("Nombre del negocio", { exact: true })
      .fill("Edición UI");
    await page
      .getByLabel("Electricidad por kWh", { exact: true })
      .fill("1234.5678");
    await page.getByLabel("Diseño por hora", { exact: true }).fill("");
    await page.getByLabel("Soporte por hora", { exact: true }).fill("0");
    await page
      .getByLabel("Zona horaria IANA", { exact: true })
      .fill("Zona/Inexistente");
    await page
      .getByLabel("Confirmo el reemplazo completo de la configuración.", {
        exact: true,
      })
      .check();
    await page
      .getByRole("button", { name: "Guardar configuración", exact: true })
      .click();
    await expect(page.getByRole("alert")).toBeVisible();
    expect(
      (await (await request.get(`${api}/settings`)).json()).business_name,
    ).toBe(baseline.business_name);
    await page
      .getByLabel("Zona horaria IANA", { exact: true })
      .fill(original.timezone);
    await page
      .getByRole("combobox", { name: "Política de seña", exact: true })
      .selectOption("required");
    await page
      .getByRole("combobox", { name: "Tipo de seña", exact: true })
      .selectOption("percentage");
    await page.getByLabel("Valor de seña", { exact: true }).fill("101");
    await page
      .getByRole("button", { name: "Guardar configuración", exact: true })
      .click();
    await expect(page.getByRole("alert")).toContainText("100");
    await page.getByLabel("Valor de seña", { exact: true }).fill("25.1234");
    await page
      .getByRole("button", { name: "Guardar configuración", exact: true })
      .click();
    await expect(
      page.getByText("Operación registrada.", { exact: true }),
    ).toBeVisible();
    const saved = await (await request.get(`${api}/settings`)).json();
    expect(saved).toEqual({
      ...baseline,
      business_name: "Edición UI",
      electricity_price_per_kwh: "1234.5678",
      design_hour_rate: null,
      support_hour_rate: "0",
      deposit_policy: "required",
      deposit_type: "percentage",
      deposit_value: "25.1234",
    });
    // Una edición externa no debe ser sobreescrita desde un formulario viejo.
    expect(
      (
        await request.put(`${api}/settings`, {
          data: { ...saved, region: "Región externa" },
        })
      ).ok(),
    ).toBe(true);
    let writes = 0;
    await page.route("**/api/v1/settings", async (route) => {
      if (route.request().method() === "PUT") writes++;
      await route.continue();
    });
    await page
      .getByLabel("Nombre del negocio", { exact: true })
      .fill("Borrador local");
    await page
      .getByLabel("Confirmo el reemplazo completo de la configuración.", {
        exact: true,
      })
      .check();
    await page
      .getByRole("button", { name: "Guardar configuración", exact: true })
      .click();
    await expect(page.getByRole("alert")).toContainText("cambió desde");
    expect(writes).toBe(0);
    await expect(
      page.getByLabel("Nombre del negocio", { exact: true }),
    ).toHaveValue("Borrador local");
    await page
      .getByRole("button", { name: "Cargar valores guardados", exact: true })
      .click();
    await expect(page.getByLabel("Región", { exact: true })).toHaveValue(
      "Región externa",
    );
    await expect(
      page.getByLabel("Nombre del negocio", { exact: true }),
    ).toHaveValue("Edición UI");
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
    await page.screenshot({ path: "test-results/installation-mobile.png" });
  } finally {
    expect(
      (await request.put(`${api}/settings`, { data: original })).ok(),
    ).toBe(true);
  }
});
test("Instalación: respuesta perdida persiste, no reenvía y permite cargar datos confirmados", async ({
  page,
  request,
}) => {
  const original = await (await request.get(`${api}/settings`)).json();
  try {
    page.on("dialog", (dialog) => dialog.accept());
    await page.goto("/settings");
    let writes = 0;
    await page.route("**/api/v1/settings", async (route) => {
      if (route.request().method() !== "PUT") return route.continue();
      writes++;
      const response = await route.fetch();
      expect(response.ok()).toBe(true);
      await route.abort();
    });
    await page
      .getByLabel("Nombre del negocio", { exact: true })
      .fill("Guardado incierto E2E");
    await page
      .getByLabel("Confirmo el reemplazo completo de la configuración.", {
        exact: true,
      })
      .check();
    await page
      .getByRole("button", { name: "Guardar configuración", exact: true })
      .click();
    const review = page.getByRole("region", {
      name: "Revisar operación incierta",
    });
    await expect(review).toBeVisible();
    await page.reload();
    await expect(review).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Guardar configuración", exact: true }),
    ).toBeDisabled();
    await review
      .getByRole("button", {
        name: "Consultar registros actuales",
        exact: true,
      })
      .click();
    await review
      .getByLabel("Ya revisé los registros y el resultado de la operación.", {
        exact: true,
      })
      .check();
    await review
      .getByRole("button", { name: "Habilitar nueva operación", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Cargar valores guardados", exact: true })
      .click();
    await expect(
      page.getByLabel("Nombre del negocio", { exact: true }),
    ).toHaveValue("Guardado incierto E2E");
    expect(writes).toBe(1);
  } finally {
    expect(
      (await request.put(`${api}/settings`, { data: original })).ok(),
    ).toBe(true);
  }
});
test("Instalación: error inicial no permite guardar una configuración vacía", async ({
  page,
}) => {
  await page.route("**/api/v1/settings", (route) =>
    route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Configuración no disponible" }),
    }),
  );
  await page.goto("/settings");
  await expect(page.getByRole("alert")).toContainText(
    "Configuración no disponible",
  );
  await expect(
    page.getByRole("button", { name: "Guardar configuración", exact: true }),
  ).toHaveCount(0);
});
