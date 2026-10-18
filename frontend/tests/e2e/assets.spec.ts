import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const api = process.env.RRII_E2E_API_BASE!;

for (const width of [360, 1440]) {
  test(`biblioteca con API real: archivos, historia y restauración ${width}px`, async ({
    page,
    request,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    const name = `Biblioteca ${width} ${Date.now()}`;
    const runtimeErrors: string[] = [];
    page.on("pageerror", (error) => runtimeErrors.push(error.message));
    await page.goto("/assets");
    await expect(
      page.getByRole("heading", { name: "Biblioteca de Assets" }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Crear recurso", exact: true })
      .click();
    await page.getByLabel("Nombre", { exact: true }).fill(name);
    await page
      .getByLabel("Descripción", { exact: true })
      .fill("Prueba aislada de biblioteca");
    await page
      .getByRole("button", { name: "Guardar recurso", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name, exact: true }),
    ).toBeVisible();
    await expect(page).toHaveURL(/\/assets\/[0-9a-f-]{36}$/);
    const id = page.url().split("/").at(-1)!;
    await page.getByLabel("Archivo para cargar").setInputFiles({
      name: "pieza.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("contenido de prueba"),
    });
    await page
      .getByRole("button", { name: "Adjuntar archivo", exact: true })
      .click();
    await expect(page.getByRole("main").getByRole("status")).toContainText(
      "Archivo adjuntado correctamente",
    );
    const downloadPromise = page.waitForEvent("download");
    await page
      .getByRole("link", { name: "Descargar pieza.txt", exact: true })
      .click();
    expect((await downloadPromise).suggestedFilename()).toBe("pieza.txt");
    const png = await page.evaluate(() => {
      const canvas = document.createElement("canvas");
      canvas.width = 200;
      canvas.height = 100;
      const context = canvas.getContext("2d")!;
      context.fillStyle = "#147b4d";
      context.fillRect(0, 0, 200, 100);
      return canvas.toDataURL("image/png").split(",")[1]!;
    });
    await page.getByLabel("Uso del archivo").selectOption("thumbnail");
    await page.getByLabel("Archivo para cargar").setInputFiles({
      name: "original.png",
      mimeType: "image/png",
      buffer: Buffer.from(png, "base64"),
    });
    await page
      .getByRole("button", { name: "Adjuntar archivo", exact: true })
      .click();
    await expect(
      page.getByRole("img", { name: "Miniatura de la revisión" }),
    ).toHaveJSProperty("naturalWidth", 200);
    await page.reload();
    await expect(
      page.getByRole("link", { name: "Descargar pieza.txt" }),
    ).toBeVisible();
    // Conflicto real del backend, sin perder el nombre del archivo elegido.
    await page.getByLabel("Archivo para cargar").setInputFiles({
      name: "pieza.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("otro contenido"),
    });
    await page
      .getByRole("button", { name: "Adjuntar archivo", exact: true })
      .click();
    await expect(page.getByRole("alert")).toContainText(
      "El nombre ya está adjunto",
    );
    await expect(page.getByLabel("Nombre del adjunto")).toHaveValue(
      "pieza.txt",
    );
    await page
      .getByRole("button", { name: "Crear nueva revisión", exact: true })
      .click();
    await expect(
      page.getByText("Esta revisión todavía no tiene archivos."),
    ).toBeVisible();
    await page.getByLabel("Comparar con revisión").selectOption({ label: "1" });
    await page
      .getByRole("button", { name: "Comparar archivos", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Agregados (2)" }),
    ).toBeVisible();
    await page
      .getByLabel("Revisión", { exact: true })
      .selectOption({ label: "1 · Histórica" });
    await expect(
      page.getByRole("link", { name: "Descargar pieza.txt" }),
    ).toBeVisible();
    await page.locator("summary").click();
    await page
      .getByRole("button", { name: "Restaurar esta revisión", exact: true })
      .click();
    await expect(
      page.getByLabel("Revisión", { exact: true }).locator("option:checked"),
    ).toHaveText("3 · Actual");
    await expect(
      page.getByRole("img", { name: "Miniatura de la revisión" }),
    ).toHaveJSProperty("naturalWidth", 200);
    const revisions = await request.get(`${api}/assets/${id}/revisions`);
    expect(revisions.ok()).toBe(true);
    expect(await revisions.json()).toHaveLength(3);
    for (const mode of ["dark", "light"]) {
      if (mode === "light")
        await page
          .getByRole("button", { name: "Cambiar claro / oscuro" })
          .click();
      await expect(page.locator("html")).toHaveClass(new RegExp(mode));
      const result = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();
      expect(result.violations).toEqual([]);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
      await page.screenshot({
        path: `test-results/assets-${width}-${mode}.png`,
        fullPage: true,
      });
    }
    await page
      .getByRole("button", { name: "Archivar recurso", exact: true })
      .click();
    await expect(
      page.getByText(
        "Este recurso está archivado. Su historia y archivos se conservan.",
      ),
    ).toBeVisible();
    await page.getByRole("link", { name: "Volver a la Biblioteca" }).click();
    await page.getByLabel("Ver archivados").check();
    await page.getByLabel("Buscar recursos", { exact: true }).fill(name);
    await page.getByRole("button", { name: "Buscar", exact: true }).click();
    await expect(page.getByRole("link", { name, exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name, exact: true })).toHaveAttribute(
      "href",
      `/assets/${id}`,
    );
    expect(runtimeErrors).toEqual([]);
  });
}

test("biblioteca: estado vacío, error recuperable y navegación por teclado", async ({
  page,
}) => {
  await page.goto("/assets");
  await page
    .getByLabel("Buscar recursos", { exact: true })
    .fill(`inexistente-${Date.now()}`);
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await expect(
    page.getByText("No hay recursos para esta búsqueda."),
  ).toBeVisible();
  await page.route("**/api/v1/assets?*", (route) => route.abort());
  await page
    .getByLabel("Buscar recursos", { exact: true })
    .fill("desconectado");
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("conexión");
  await page.unroute("**/api/v1/assets?*");
  await page.getByRole("button", { name: "Volver a intentar" }).click();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Biblioteca de Assets", exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Saltar al contenido" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
  await page
    .getByRole("button", { name: "Crear recurso", exact: true })
    .click();
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(result.violations).toEqual([]);
});
