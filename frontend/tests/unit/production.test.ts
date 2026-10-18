import { afterEach, expect, test, vi } from "vitest";
import { productionApi } from "../../app/features/production/api";
import { ApiError } from "../../app/features/shared/http";
afterEach(() => vi.unstubAllGlobals());
test("plan conserva precisión, selecciones vacías explícitas y efectos elegidos en cada origen", async () => {
  const requests: Request[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    requests.push(request);
    return new Response("{}", {
      headers: { "Content-Type": "application/json" },
    });
  });
  const api = productionApi("http://api.test/api/v1");
  const body = {
    request_id: "request",
    recipe_id: "recipe",
    variant_id: "variant",
    target_quantity: "999999999999.000001",
    selections: [{ definition_id: "option", values: [] }],
    reserve_supplies: false,
    allocate_output: false,
    machine_assignments: {},
  };
  await api.create({ kind: "order", id: "order" }, body);
  await api.create({ kind: "component", id: "component" }, body);
  expect(requests.map((row) => row.url)).toEqual([
    "http://api.test/api/v1/orders/order/production-plans",
    "http://api.test/api/v1/project-components/component/production-plans",
  ]);
  expect(await requests[0]!.json()).toEqual(body);
  expect(await requests[1]!.json()).toEqual(body);
});
test("inicio distingue máquina omitida y ejecución explícita sin máquina; filtros van al servidor", async () => {
  const requests: Request[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    requests.push(request);
    return new Response("{}", {
      headers: { "Content-Type": "application/json" },
    });
  });
  const api = productionApi("http://api.test");
  await api.start("task", { request_id: "first" });
  await api.start("task", { request_id: "second", machine_id: null });
  await api.tasks({ order_id: "order", status: "paused", priority: "high" });
  expect(await requests[0]!.json()).toEqual({ request_id: "first" });
  expect(await requests[1]!.json()).toEqual({
    request_id: "second",
    machine_id: null,
  });
  const url = new URL(requests[2]!.url);
  expect(url.searchParams.get("order_id")).toBe("order");
  expect(url.searchParams.get("status")).toBe("paused");
  expect(url.searchParams.get("priority")).toBe("high");
});
test("error de prerequisitos conserva el conflicto HTTP para no reintentar como transporte incierto", async () => {
  vi.stubGlobal(
    "fetch",
    async () =>
      new Response(
        JSON.stringify({ detail: "Hay prerrequisitos sin finalizar" }),
        { status: 409, headers: { "Content-Type": "application/json" } },
      ),
  );
  const operation = productionApi("http://api.test").start("task", {
    request_id: "request",
  });
  await expect(operation).rejects.toBeInstanceOf(ApiError);
  await expect(operation).rejects.toMatchObject({
    status: 409,
    message: "Hay prerrequisitos sin finalizar",
  });
});
