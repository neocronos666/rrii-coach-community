import AxeBuilder from "@axe-core/playwright";
import { expect, test, type APIRequestContext } from "@playwright/test";
const api = process.env.RRII_E2E_API_BASE!;
async function seed(request: APIRequestContext, count = 1) {
  const calculationResponse = await request.post(`${api}/cost-calculations`, {
    data: {
      extras: [
        {
          description: "Preparación comercial",
          amount: "100.87",
          currency: "ARS",
        },
      ],
    },
  });
  expect(calculationResponse.ok(), await calculationResponse.text()).toBe(true);
  const calculation = await calculationResponse.json();
  const response = await request.post(`${api}/quotes`, {
    data: {
      title: `Comercial ${Date.now()}`,
      markup_percentage: "0",
      items: Array.from({ length: count }, (_, i) => ({
        cost_calculation_id: calculation.id,
        description: `Pieza ${i + 1}`,
        quantity: "1.000001",
      })),
    },
  });
  expect(response.ok(), await response.text()).toBe(true);
  return {
    quote: await response.json(),
    calculation: await (
      await request.get(`${api}/cost-calculations/${calculation.id}`)
    ).json(),
  };
}
async function destinations(request: APIRequestContext, id: string) {
  const orders = await (await request.get(`${api}/orders`)).json();
  const projects = await (await request.get(`${api}/projects`)).json();
  return [...orders, ...projects].filter(
    (row: { source_quote_id: string }) => row.source_quote_id === id,
  );
}
for (const width of [360, 1440]) {
  test(`comercial: edición, aprobación, conversión y cancelación ${width}px`, async ({
    page,
    request,
  }) => {
    test.setTimeout(120000);
    await page.setViewportSize({ width, height: 960 });
    const { quote, calculation } = await seed(request, width === 360 ? 1 : 2);
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(`/quotes/${quote.id}`);
    await page
      .getByRole("button", { name: "Editar presupuesto", exact: true })
      .click();
    await page
      .getByLabel("Título comercial", { exact: true })
      .fill(`${quote.title} revisada`);
    await page
      .getByLabel("Modificar condiciones económicas", { exact: true })
      .check();
    await page
      .getByLabel("Indicar precio final manual", { exact: true })
      .check();
    await page
      .getByLabel("Total final propuesto", { exact: true })
      .fill("123.87");
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
          .analyze()
      ).violations,
    ).toEqual([]);
    await page
      .getByRole("button", { name: "Guardar cambios comerciales", exact: true })
      .click();
    await expect(page.getByTestId("formal-total")).toHaveText("ARS 123.0000");
    expect(
      await (
        await request.get(`${api}/cost-calculations/${calculation.id}`)
      ).json(),
    ).toEqual(calculation);
    await expect(
      page.getByRole("button", { name: "Aprobar presupuesto", exact: true }),
    ).toBeDisabled();
    await page
      .getByLabel("Confirmo la aprobación del presupuesto guardado", {
        exact: true,
      })
      .check();
    await page
      .getByRole("button", { name: "Aprobar presupuesto", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Editar presupuesto", exact: true }),
    ).toHaveCount(0);
    expect(await destinations(request, quote.id)).toHaveLength(0);
    await page
      .getByLabel("Confirmo la conversión del presupuesto aprobado", {
        exact: true,
      })
      .check();
    await page
      .getByRole("button", { name: "Convertir presupuesto", exact: true })
      .click();
    const kind = width === 360 ? "orders" : "projects";
    await expect(page).toHaveURL(new RegExp(`/${kind}/[0-9a-f-]{36}$`));
    await expect(page.getByTestId("destination-total")).toHaveText(
      "ARS 123.0000",
    );
    const [destination] = await destinations(request, quote.id);
    expect(await destinations(request, quote.id)).toHaveLength(1);
    const firstSnapshot = await (
      await request.get(`${api}/${kind}/${destination.id}`)
    ).json();
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
      await page.screenshot({
        path: `test-results/commercial-${width}-${mode}.png`,
      });
    }
    await page.getByLabel("Confirmo la cancelación", { exact: true }).check();
    await page.getByRole("button", { name: "Cancelar", exact: true }).click();
    await expect(page.getByTestId("destination-status")).toHaveText(
      "Cancelado",
    );
    const after = await (
      await request.get(`${api}/${kind}/${destination.id}`)
    ).json();
    expect(after.quoted_final_price).toBe(firstSnapshot.quoted_final_price);
    expect(after.source_quote_id).toBe(quote.id);
    await page
      .getByRole("link", { name: "Ver presupuesto de origen", exact: true })
      .click();
    await expect(
      page.getByRole("link", { name: /Abrir destino/ }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Convertir presupuesto", exact: true }),
    ).toHaveCount(0);
    await page.goto(`/${kind}`);
    await expect(
      page.getByRole("link", {
        name: `${destination.code} · ${quote.title} revisada`,
        exact: true,
      }),
    ).toBeVisible();
    expect(errors).toEqual([]);
  });
}
test("comercial: respuestas perdidas en aprobación y conversión consultan o recuperan sin duplicar", async ({
  page,
  request,
}) => {
  const { quote } = await seed(request);
  let approvals = 0,
    conversions = 0;
  await page.route(`**/api/v1/quotes/${quote.id}/approve`, async (route) => {
    approvals++;
    await route.fetch();
    await route.abort("failed");
  });
  await page.goto(`/quotes/${quote.id}`);
  await page
    .getByLabel("Confirmo la aprobación del presupuesto guardado", {
      exact: true,
    })
    .check();
  await page
    .getByRole("button", { name: "Aprobar presupuesto", exact: true })
    .click();
  await expect(
    page.getByText("Estado comercial: Aprobado", { exact: true }),
  ).toBeVisible();
  expect(approvals).toBe(1);
  await page.route(`**/api/v1/quotes/${quote.id}/convert`, async (route) => {
    conversions++;
    const response = await route.fetch();
    if (conversions === 1) await route.abort("failed");
    else await route.fulfill({ response });
  });
  await page
    .getByLabel("Confirmo la conversión del presupuesto aprobado", {
      exact: true,
    })
    .check();
  await page
    .getByRole("button", { name: "Convertir presupuesto", exact: true })
    .click();
  await expect(
    page.getByRole("button", {
      name: "Reintentar solicitud pendiente",
      exact: true,
    }),
  ).toBeVisible();
  await page.reload();
  await expect(page.getByRole("link", { name: /Abrir destino/ })).toBeVisible();
  await page
    .getByRole("button", {
      name: "Reintentar solicitud pendiente",
      exact: true,
    })
    .click();
  await expect(page).toHaveURL(/\/orders\/[0-9a-f-]{36}$/);
  expect(conversions).toBe(2);
  expect(await destinations(request, quote.id)).toHaveLength(1);
});
test("comercial: rechazo y conflicto conservan el estado y la edición", async ({
  page,
  request,
}) => {
  const { quote } = await seed(request);
  await page.goto(`/quotes/${quote.id}`);
  await page
    .getByLabel("Motivo del rechazo", { exact: true })
    .fill("Cliente no acepta");
  await page
    .getByLabel("Confirmo el rechazo del presupuesto guardado", { exact: true })
    .check();
  await page
    .getByRole("button", { name: "Rechazar presupuesto", exact: true })
    .click();
  await expect(
    page.getByText("Motivo del rechazo: Cliente no acepta", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Convertir presupuesto", exact: true }),
  ).toHaveCount(0);
  const second = (await seed(request)).quote;
  await page.goto(`/quotes/${second.id}`);
  await page
    .getByRole("button", { name: "Editar presupuesto", exact: true })
    .click();
  await page
    .getByLabel("Título comercial", { exact: true })
    .fill("Edición conservada");
  expect((await request.post(`${api}/quotes/${second.id}/approve`)).ok()).toBe(
    true,
  );
  await page
    .getByRole("button", { name: "Guardar cambios comerciales", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("draft");
  await expect(
    page.getByLabel("Título comercial", { exact: true }),
  ).toHaveValue("Edición conservada");
  await expect(
    page.getByRole("button", {
      name: "Guardar cambios comerciales",
      exact: true,
    }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Descartar edición", exact: true })
    .click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    second.title,
  );
});

test("comercial: respuesta perdida al editar conserva entradas y permite consultar lo guardado", async ({
  page,
  request,
}) => {
  const { quote } = await seed(request);
  let writes = 0;
  await page.route(`**/api/v1/quotes/${quote.id}`, async (route) => {
    if (route.request().method() !== "PATCH") return route.continue();
    writes++;
    expect(route.request().postDataJSON()).toEqual({
      title: "Título confirmado en servidor",
    });
    await route.fetch();
    await route.abort("failed");
  });
  await page.goto(`/quotes/${quote.id}`);
  await page
    .getByRole("button", { name: "Editar presupuesto", exact: true })
    .click();
  await page
    .getByLabel("Título comercial", { exact: true })
    .fill("Título confirmado en servidor");
  await page
    .getByRole("button", { name: "Guardar cambios comerciales", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "No se recibió una confirmación",
  );
  await expect(
    page.getByLabel("Título comercial", { exact: true }),
  ).toHaveValue("Título confirmado en servidor");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Título confirmado en servidor",
  );
  expect(writes).toBe(1);
  await page
    .getByRole("button", { name: "Descartar edición", exact: true })
    .click();
  await expect(page.getByTestId("formal-total")).toHaveText(
    `ARS ${quote.breakdown.final_price}`,
  );
});
