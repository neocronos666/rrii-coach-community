import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
const api = process.env.RRII_E2E_API_BASE!;
for (const width of [360, 1440]) {
  test(`producto, opciones y receta con API real ${width}px`, async ({
    page,
    request,
  }) => {
    test.setTimeout(240000);
    await page.setViewportSize({ width, height: 900 });
    const suffix = `${width}-${Date.now()}`,
      name = `Producto ${suffix}`,
      definition = `Terminación ${suffix}`,
      value = `Pulido ${suffix}`,
      service = `Terminar ${suffix}`;
    const runtime: string[] = [];
    page.on("pageerror", (error) => runtime.push(error.message));
    const familyResponse = await request.post(`${api}/asset-families`, {
      data: { name: `Familia ${suffix}` },
    });
    expect(familyResponse.ok()).toBe(true);
    const family = (await familyResponse.json()).id;
    const assetResponse = await request.post(`${api}/assets`, {
      data: { name: `Diseño ${suffix}`, family_id: family },
    });
    expect(assetResponse.ok()).toBe(true);
    const asset = await assetResponse.json();
    const supplyResponse = await request.post(`${api}/supplies`, {
      data: {
        name: `Material ${suffix}`,
        category: "material",
        base_unit: "g",
      },
    });
    expect(supplyResponse.ok()).toBe(true);
    await page.goto("/products");
    await page
      .getByRole("button", { name: "Crear producto", exact: true })
      .click();
    await page.getByLabel("Nombre del producto", { exact: true }).fill(name);
    await page
      .getByLabel("Nombre de la variante", { exact: true })
      .fill("Estándar");
    await page
      .getByRole("button", { name: "Guardar producto", exact: true })
      .click();
    await expect(page).toHaveURL(/\/products\/[0-9a-f-]{36}$/);
    const id = page.url().split("/").at(-1)!;
    await page
      .getByRole("heading", { name: "Opciones del producto", exact: true })
      .waitFor();
    const options = page.locator("#product-options");
    await options
      .getByText("Crear características y valores reutilizables", {
        exact: true,
      })
      .click();
    await options
      .getByLabel("Nombre de la característica", { exact: true })
      .fill(definition);
    await options
      .getByRole("button", { name: "Crear característica", exact: true })
      .click();
    await expect(
      options
        .getByRole("combobox", { name: "Característica", exact: true })
        .last()
        .locator("option:checked"),
    ).toHaveText(definition);
    await options.getByLabel("Nombre del valor", { exact: true }).fill(value);
    await options
      .getByRole("combobox", {
        name: "Familia de diseño (opcional)",
        exact: true,
      })
      .selectOption(family);
    await options
      .getByRole("combobox", {
        name: "Insumo vinculado (opcional)",
        exact: true,
      })
      .selectOption({ label: `Material ${suffix} (g)` });
    await options
      .getByRole("button", { name: "Crear valor", exact: true })
      .click();
    await expect(
      options.getByLabel("Nombre del valor", { exact: true }),
    ).toHaveValue("");
    await options
      .getByRole("button", {
        name: "Agregar característica al producto",
        exact: true,
      })
      .click();
    const feature = options.getByRole("region", {
      name: definition,
      exact: true,
    });
    await feature
      .getByRole("button", { name: "Agregar valor permitido", exact: true })
      .click();
    await feature
      .getByRole("combobox", { name: "Valor", exact: true })
      .selectOption({ label: value });
    await options
      .getByRole("button", { name: "Guardar opciones", exact: true })
      .click();
    await expect(options.getByRole("status")).toHaveText("Cambios guardados.");
    const recipe = page.locator("#product-recipe");
    await recipe
      .getByLabel("Nombre de la receta", { exact: true })
      .fill("Receta base");
    await recipe
      .getByRole("button", { name: "Crear receta base", exact: true })
      .click();
    await expect(
      recipe.getByRole("heading", { name: "Pasos de la receta", exact: true }),
    ).toBeVisible();
    await recipe
      .getByText("Crear servicio reutilizable", { exact: true })
      .click();
    await recipe
      .getByLabel("Nombre del servicio", { exact: true })
      .fill(service);
    await recipe
      .getByLabel("Frase personalizada (opcional)", { exact: true })
      .fill("Terminar {quantity} de {product}");
    await recipe
      .getByRole("button", { name: "Crear servicio", exact: true })
      .click();
    await expect(
      recipe.getByLabel("Nombre del servicio", { exact: true }),
    ).toHaveValue("");
    await recipe
      .getByRole("button", { name: "Agregar paso", exact: true })
      .click();
    const step1 = recipe.getByRole("region", {
      name: "Pasos de la receta 1",
      exact: true,
    });
    await step1.getByLabel("Título del paso", { exact: true }).fill("Preparar");
    await step1
      .getByRole("combobox", { name: "Clase de paso", exact: true })
      .selectOption("print");
    await step1
      .getByRole("combobox", { name: "Tipo de tarea", exact: true })
      .selectOption("fdm_print");
    const fixed = step1
      .locator("details")
      .filter({
        has: page.locator("summary").filter({ hasText: /^Recursos de diseño/ }),
      });
    await fixed.locator("summary").click();
    await fixed
      .getByRole("button", { name: "Agregar revisión fija", exact: true })
      .click();
    await fixed
      .getByRole("combobox", { name: "Recurso", exact: true })
      .selectOption(asset.id);
    await fixed
      .getByRole("combobox", { name: "Revisión", exact: true })
      .selectOption(asset.current_revision_id);
    await fixed
      .getByLabel("Cantidad por lote", { exact: true })
      .fill("1.000001");
    const materials = step1
      .locator("details")
      .filter({
        has: page.locator("summary").filter({ hasText: /^Insumos fijos/ }),
      });
    await materials.locator("summary").click();
    await materials
      .getByRole("button", { name: "Agregar insumo fijo", exact: true })
      .click();
    await materials
      .getByRole("combobox", { name: "Insumo", exact: true })
      .selectOption({ label: `Material ${suffix} (g)` });
    await materials
      .getByLabel("Cantidad por lote", { exact: true })
      .fill("0.123456");
    await recipe
      .getByRole("button", { name: "Agregar paso", exact: true })
      .click();
    const step2 = recipe.getByRole("region", {
      name: "Pasos de la receta 2",
      exact: true,
    });
    await step2.getByLabel("Título del paso", { exact: true }).fill("Terminar");
    await step2
      .getByRole("combobox", { name: "Clase de paso", exact: true })
      .selectOption("service");
    await step2
      .getByRole("combobox", { name: "Servicio del catálogo", exact: true })
      .selectOption({ label: service });
    await step2.getByLabel("Preparar", { exact: true }).check();
    await step2
      .getByLabel("Realizar sólo cuando se seleccione una opción", {
        exact: true,
      })
      .check();
    await step2
      .getByRole("combobox", { name: "Característica", exact: true })
      .selectOption({ label: definition });
    await step2
      .getByRole("combobox", { name: "Valor", exact: true })
      .selectOption({ label: value });
    await step2
      .getByLabel("Multiplicar demanda por la cantidad seleccionada", {
        exact: true,
      })
      .check();
    await recipe
      .getByRole("button", { name: "Agregar paso", exact: true })
      .click();
    const step3 = recipe.getByRole("region", {
      name: "Pasos de la receta 3",
      exact: true,
    });
    await step3.getByLabel("Título del paso", { exact: true }).fill("Entregar");
    await step3.getByLabel("Salida final", { exact: true }).check();
    await step3.getByLabel("Terminar", { exact: true }).check();
    const dynamic = step2
      .locator("details")
      .filter({
        has: page.locator("summary").filter({ hasText: /^Recursos de diseño/ }),
      });
    await dynamic.locator("summary").click();
    await dynamic
      .getByRole("button", {
        name: "Agregar recurso desde opción",
        exact: true,
      })
      .click();
    await dynamic
      .getByRole("combobox", { name: "Característica", exact: true })
      .selectOption({ label: definition });
    await dynamic
      .getByRole("combobox", { name: "Valor", exact: true })
      .selectOption({ label: value });
    const selectedMaterial = step2
      .locator("details")
      .filter({
        has: page
          .locator("summary")
          .filter({ hasText: /^Materiales desde opciones/ }),
      });
    await selectedMaterial.locator("summary").click();
    await selectedMaterial
      .getByRole("button", {
        name: "Agregar material desde opción",
        exact: true,
      })
      .click();
    await selectedMaterial
      .getByRole("combobox", { name: "Característica", exact: true })
      .selectOption({ label: definition });
    await selectedMaterial
      .getByRole("combobox", { name: "Unidad", exact: true })
      .selectOption("g");
    await selectedMaterial
      .getByLabel("Cantidad por lote", { exact: true })
      .fill("0.000001");

    await recipe
      .getByRole("button", { name: "Guardar pasos", exact: true })
      .click();
    await expect(recipe.getByRole("status")).toHaveText("Cambios guardados.");
    const recipeResponse = await request.get(`${api}/products/${id}/recipe`);
    expect(recipeResponse.ok()).toBe(true);
    const recipeId = (await recipeResponse.json()).id;
    await expect
      .poll(async () => {
        const res = await request.get(`${api}/recipes/${recipeId}/plan`);
        return (await res.json()).steps.length;
      })
      .toBe(3);
    await page.reload();
    await expect(
      page.getByLabel("Título del paso", { exact: true }),
    ).toHaveCount(3);
    await expect(
      step2.getByLabel("Multiplicar demanda por la cantidad seleccionada", {
        exact: true,
      }),
    ).toBeChecked();
    const preview = page.locator("#product-preview");
    await preview
      .getByRole("combobox", { name: "Variante", exact: true })
      .selectOption({ label: "Estándar" });
    await preview
      .getByLabel("Cantidad de productos", { exact: true })
      .fill("3");
    await preview
      .getByRole("button", { name: "Resolver receta", exact: true })
      .click();
    await expect(
      preview.getByText("Pasos omitidos: step_2", { exact: true }),
    ).toBeVisible();
    await preview
      .getByRole("combobox", { name: "Modo de selección", exact: true })
      .selectOption("explicit");
    await preview
      .getByRole("button", { name: "Agregar selección", exact: true })
      .click();
    await preview
      .getByRole("combobox", { name: "Valor", exact: true })
      .selectOption({ label: value });
    await preview
      .getByLabel("Cantidad seleccionada", { exact: true })
      .fill("2");
    await preview
      .getByRole("button", { name: "Resolver receta", exact: true })
      .click();
    await expect(
      preview.getByText(`Acción del servicio: Terminar 6 de ${name}`, {
        exact: true,
      }),
    ).toBeVisible();
    // Un ciclo se rechaza y no altera el plan persistido ni borra el borrador.
    await step1.getByLabel("Entregar", { exact: true }).check();
    await recipe
      .getByRole("button", { name: "Guardar pasos", exact: true })
      .click();
    await expect(recipe.getByRole("alert")).toContainText("DAG");
    expect(
      (await (await request.get(`${api}/recipes/${recipeId}/plan`)).json())
        .steps[0].depends_on,
    ).toEqual([]);
    await expect(step1.getByLabel("Entregar", { exact: true })).toBeChecked();
    await step1.getByLabel("Entregar", { exact: true }).uncheck();
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
      await preview.screenshot({
        path: `test-results/products-preview-${width}-${mode}.png`,
      });
      await page.evaluate(() =>
        window.scrollTo({ top: 0, behavior: "instant" }),
      );
      await page.screenshot({
        path: `test-results/products-${width}-${mode}.png`,
        fullPage: false,
      });
    }
    await step1
      .getByLabel("Título del paso", { exact: true })
      .fill("Borrador pendiente");
    page.once("dialog", (dialog) => dialog.dismiss());
    await page
      .getByRole("link", { name: "Volver a Productos", exact: true })
      .click();
    await expect(page).toHaveURL(new RegExp(`/products/${id}$`));
    await expect(
      step1.getByLabel("Título del paso", { exact: true }),
    ).toHaveValue("Borrador pendiente");
    expect(runtime).toEqual([]);
  });
}

test("catálogo: variantes, unidad inmutable y error recuperable", async ({
  page,
}) => {
  const name = `Variantes ${Date.now()}`;
  await page.goto("/products");
  await page
    .getByRole("button", { name: "Crear producto", exact: true })
    .click();
  await page.getByLabel("Nombre del producto", { exact: true }).fill(name);
  await page
    .getByLabel("Nombre de la variante", { exact: true })
    .fill("Original");
  await page
    .getByRole("button", { name: "Guardar producto", exact: true })
    .click();
  await expect(page).toHaveURL(/\/products\/[0-9a-f-]{36}$/);
  const variants = page.locator("#product-variants");
  await variants
    .getByRole("button", { name: "Agregar variante", exact: true })
    .click();
  await variants
    .getByLabel("Nombre de la variante", { exact: true })
    .fill("Segunda");
  await variants.getByLabel("SKU", { exact: true }).fill(`sku-${Date.now()}`);
  await variants
    .getByRole("button", { name: "Guardar variante", exact: true })
    .click();
  await expect(variants.getByText("Segunda", { exact: true })).toBeVisible();
  await variants
    .getByRole("button", { name: "Editar variante · Segunda", exact: true })
    .click();
  await expect(
    variants.getByRole("combobox", { name: "Unidad", exact: true }),
  ).toBeDisabled();
  await variants
    .getByLabel("Nombre de la variante", { exact: true })
    .fill("Revisada");
  await variants
    .getByRole("button", { name: "Guardar variante", exact: true })
    .click();
  await expect(variants.getByText("Revisada", { exact: true })).toBeVisible();
  await page
    .getByRole("link", { name: "Volver a Productos", exact: true })
    .click();
  await expect(page).toHaveURL(/\/products$/);
  await page.route("**/api/v1/products?*", (route) => route.abort());
  await page.getByLabel("Buscar productos", { exact: true }).fill(name);
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("conexión");
  await page.unroute("**/api/v1/products?*");
  await page
    .getByRole("button", { name: "Volver a intentar", exact: true })
    .click();
  await expect(page.getByRole("link", { name, exact: true })).toBeVisible();
});
