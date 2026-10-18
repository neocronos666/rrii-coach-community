import { afterEach, expect, test, vi } from "vitest";
import { testPrintApi } from "../../app/features/test-prints/api";
import { ApiError } from "../../app/features/shared/http";
import {
  stepSnapshot,
  omittedKeys,
  configurationSnapshot,
  orderedSteps,
} from "../../app/features/test-prints/snapshots";
afterEach(() => vi.unstubAllGlobals());
test("crear, iniciar, cerrar y promover conservan identidad y cantidades textuales", async () => {
  const requests: Request[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    requests.push(request);
    return new Response("{}", {
      headers: { "Content-Type": "application/json" },
    });
  });
  const api = testPrintApi("http://api.test/api/v1/");
  await api.create({
    request_id: "id",
    recipe_id: "recipe",
    variant_id: "variant",
    target_quantity: "0.000001",
    selections: [{ definition_id: "option", values: [] }],
  });
  await api.start("test", "step", { request_id: "run" });
  await api.start("test", "step", { request_id: "run-null", machine_id: null });
  await api.close("run", {
    good_quantity: "0.123456",
    failed_quantity: "0",
    actual_duration_seconds: null,
    supply_consumptions: [
      {
        supply_id: "supply",
        consumed: "123456789012.123456",
        wasted: "0.000001",
      },
    ],
    product_consumptions: [{ variant_id: "part", consumed: "1", wasted: "0" }],
  });
  await api.promote("test", { request_id: "promotion", quantity: "0.000001" });
  expect(await requests[0]!.json()).toMatchObject({
    target_quantity: "0.000001",
    selections: [{ definition_id: "option", values: [] }],
  });
  expect(await requests[1]!.json()).not.toHaveProperty("machine_id");
  expect(await requests[2]!.json()).toHaveProperty("machine_id", null);
  expect(await requests[3]!.json()).toMatchObject({
    good_quantity: "0.123456",
    supply_consumptions: [
      { consumed: "123456789012.123456", wasted: "0.000001" },
    ],
  });
  expect(await requests[4]!.json()).toEqual({
    request_id: "promotion",
    quantity: "0.000001",
  });
});
test("los conflictos conservan estado HTTP para recuperar la edición", async () => {
  vi.stubGlobal(
    "fetch",
    async () =>
      new Response(
        JSON.stringify({ detail: "Hay prerrequisitos sin finalizar" }),
        { status: 409, headers: { "Content-Type": "application/json" } },
      ),
  );
  await expect(
    testPrintApi("http://api.test").start("test", "step", { request_id: "id" }),
  ).rejects.toBeInstanceOf(ApiError);
  await expect(
    testPrintApi("http://api.test").cancel("test"),
  ).rejects.toMatchObject({
    status: 409,
    message: "Hay prerrequisitos sin finalizar",
  });
});
test("historial de intentos recorre todas las páginas y listado conserva el filtro", async () => {
  const urls: URL[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    const url = new URL(request.url);
    urls.push(url);
    return new Response(
      JSON.stringify(
        url.searchParams.get("offset") === "0"
          ? Array.from({ length: 100 }, (_, i) => ({ id: String(i) }))
          : [],
      ),
      { headers: { "Content-Type": "application/json" } },
    );
  });
  const api = testPrintApi("http://api.test");
  expect(await api.runs("test", "step")).toHaveLength(100);
  expect(urls[1]!.searchParams.get("offset")).toBe("100");
  await api.list(24, "variant");
  expect(urls[2]!.searchParams.get("variant_id")).toBe("variant");
  expect(urls[2]!.searchParams.get("limit")).toBe("25");
  expect(await api.stockMovements("variant")).toHaveLength(100);
  expect(urls.at(-1)!.searchParams.get("offset")).toBe("100");
});
test("snapshot inválido no se interpreta como receta vacía ni cero", () => {
  expect(stepSnapshot.safeParse({ title: "Paso" }).success).toBe(false);
  const source = {
    key: "make",
    title: "Fabricar",
    kind: "manual",
    unit: "unit",
    depends_on: ["previous"],
    resources: [],
    supply_inputs: [{ supply_id: "supply", quantity_per_batch: "0.000001" }],
    product_inputs: [
      {
        product_variant_id: "part",
        quantity_per_batch: "2",
        source_step_key: "previous",
      },
    ],
  };
  expect(stepSnapshot.parse(source)).toEqual(source);
  expect(
    configurationSnapshot.parse({
      selections: [
        {
          definition_id: "option",
          values: [
            { value_id: "value", quantity: "0.000001", revision_id: null },
          ],
        },
      ],
    }).selections[0]!.values[0]!.quantity,
  ).toBe("0.000001");
  expect(omittedKeys({ omitted_step_keys: ["paint"] })).toEqual(["paint"]);
});

test("orden visual usa la posición guardada sin modificar pasos ni planificar el DAG", () => {
  const original = [
    { snapshot: { position: 3 }, key: "assembly" },
    { snapshot: { position: 0 }, key: "print" },
    { snapshot: { position: 2 }, key: "wait" },
  ];
  expect(orderedSteps(original).map((row) => row.key)).toEqual([
    "print",
    "wait",
    "assembly",
  ]);
  expect(original[0]!.key).toBe("assembly");
});

test("previsualizar envía la selección y precisión sin crear una prueba", async () => {
  const requests: Request[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    requests.push(request);
    return new Response(
      JSON.stringify({ steps: [], target_quantity: "0.000001" }),
      { headers: { "Content-Type": "application/json" } },
    );
  });
  const result = await testPrintApi("http://api.test").preview("recipe", {
    variant_id: "variant",
    target_quantity: "0.000001",
    selections: [{ definition_id: "option", values: [] }],
  });
  expect(result.target_quantity).toBe("0.000001");
  expect(requests).toHaveLength(1);
  expect(requests[0]!.url).toBe(
    "http://api.test/api/v1/recipes/recipe/production-preview",
  );
  expect(await requests[0]!.json()).toEqual({
    variant_id: "variant",
    target_quantity: "0.000001",
    selections: [{ definition_id: "option", values: [] }],
  });
});
