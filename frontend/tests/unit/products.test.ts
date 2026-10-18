import { afterEach, expect, test, vi } from "vitest";
import { productApi, type Schema } from "../../app/features/products/api";
import { newStep, stepDraft } from "../../app/features/products/drafts";
afterEach(() => vi.unstubAllGlobals());
test("editar un plan conserva precisión y referencias sin reenviar metadatos de lectura", () => {
  const row: Schema["StepRead"] = {
    ...newStep("print"),
    id: "step-id",
    position: 0,
    quantity_per_output: "123456789012.123456",
    batch_yield: "0.000001",
    parameters: { vendor: { preserve: true } },
    resources: [
      {
        key: "fixed",
        asset_revision_id: "revision",
        asset_id: "asset",
        code: "AST-1",
        name: "Diseño",
        revision_number: 4,
        archived: false,
        quantity_per_batch: "1.000001",
      },
      {
        key: "selected",
        from_selection: { definition_id: "definition", value_id: "value" },
        quantity_per_batch: "2",
      },
    ],
    supply_inputs: [{ supply_id: "supply", quantity_per_batch: "0.000001" }],
    selected_supply_inputs: [
      { definition_id: "material", unit: "g", quantity_per_batch: "10.123456" },
    ],
    product_inputs: [
      {
        product_variant_id: "part",
        source_step_key: "source",
        quantity_per_batch: "3",
      },
    ],
    service_name: "Sólo lectura",
    service_action: "Texto resuelto",
  };
  const result = stepDraft(row);
  expect(result.quantity_per_output).toBe("123456789012.123456");
  expect(result.parameters).toEqual(row.parameters);
  expect(result.selected_supply_inputs).toEqual(row.selected_supply_inputs);
  expect(result.product_inputs).toEqual(row.product_inputs);
  expect(result).not.toHaveProperty("id");
  expect(result).not.toHaveProperty("service_action");
  expect(result.resources![0]).not.toHaveProperty("asset_id");
  expect(result.resources![1]).toEqual(row.resources![1]);
  result.supply_inputs![0]!.quantity_per_batch = "99";
  expect(row.supply_inputs![0]!.quantity_per_batch).toBe("0.000001");
});
test("ausencia de receta sólo se interpreta como tal ante 404", async () => {
  let status = 404;
  vi.stubGlobal(
    "fetch",
    async () =>
      new Response(JSON.stringify({ detail: "No disponible" }), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
  );
  const api = productApi("http://api.test/api/v1");
  expect(await api.baseRecipe("product")).toBeNull();
  status = 500;
  await expect(api.baseRecipe("product")).rejects.toThrow("No disponible");
});
test("resolver transmite cantidades textuales y distingue defaults de selección vacía", async () => {
  const requests: Request[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    requests.push(request);
    return new Response("{}", {
      headers: { "Content-Type": "application/json" },
    });
  });
  const api = productApi("http://api.test/api/v1/");
  await api.resolve("product", {
    variant_id: "variant",
    quantity: "0.123456",
    selections: [],
  });
  await api.resolve("product", {
    variant_id: "variant",
    quantity: "2",
    selections: [{ definition_id: "option", values: [] }],
  });
  expect(await requests[0]!.json()).toMatchObject({
    quantity: "0.123456",
    selections: [],
  });
  expect(await requests[1]!.json()).toMatchObject({
    selections: [{ definition_id: "option", values: [] }],
  });
});
test("catálogo de valores recorre todas las páginas y preserva errores de publicación", async () => {
  const urls: URL[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    const url = new URL(request.url);
    urls.push(url);
    if (request.method === "PUT")
      return new Response(
        JSON.stringify({ detail: "Las dependencias deben formar un DAG" }),
        { status: 422, headers: { "Content-Type": "application/json" } },
      );
    return new Response(
      JSON.stringify(
        url.searchParams.get("offset") === "0"
          ? Array.from({ length: 100 }, (_, i) => ({ id: String(i) }))
          : [],
      ),
      { headers: { "Content-Type": "application/json" } },
    );
  });
  const api = productApi("http://api.test/api/v1");
  expect(await api.values("definition")).toHaveLength(100);
  expect(urls.at(-1)!.searchParams.get("offset")).toBe("100");
  await expect(api.savePlan("recipe", { steps: [] })).rejects.toThrow("DAG");
});
