import { afterEach, expect, test, vi } from "vitest";
import { inventoryApi } from "../../app/features/inventory/api";
import {
  localDateTime,
  utcDateTime,
  reviewRecord,
} from "../../app/features/inventory/values";
import { ApiError } from "../../app/features/shared/http";
afterEach(() => vi.unstubAllGlobals());
test("compra conserva decimales y fecha con zona, sin clave idempotente inventada", async () => {
  const requests: Request[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    requests.push(request);
    return new Response("{}", {
      headers: { "Content-Type": "application/json" },
    });
  });
  const body = {
    quantity: "999999999999.000001",
    presentation_id: "presentation",
    total_cost: "123456789.1234",
    currency: "ARS",
    purchased_at: "2026-10-14T13:00:00.000Z",
  };
  await inventoryApi("http://api.test/api/v1").purchase("supply", body);
  expect(requests[0]!.url).toBe(
    "http://api.test/api/v1/supplies/supply/purchases",
  );
  expect(await requests[0]!.json()).toEqual(body);
});
test("reservar envía cantidad absoluta, entregar conserva request_id y liberar no fabrica un cuerpo", async () => {
  const requests: Request[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    requests.push(request);
    return new Response("{}", {
      headers: { "Content-Type": "application/json" },
    });
  });
  const api = inventoryApi("http://api.test");
  await api.reserve("task", "supply", { quantity: "0.000000" });
  await api.deliver("allocation", {
    request_id: "same-request",
    quantity: "0.000001",
  });
  await api.release("allocation");
  expect(requests[0]!.method).toBe("PUT");
  expect(await requests[0]!.json()).toEqual({ quantity: "0.000000" });
  expect(await requests[1]!.json()).toEqual({
    request_id: "same-request",
    quantity: "0.000001",
  });
  expect(await requests[2]!.text()).toBe("");
});
test("historial de asignaciones recorre páginas sin perder filtros del origen", async () => {
  const urls: URL[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    const url = new URL(request.url);
    urls.push(url);
    return new Response(
      JSON.stringify(
        Array.from(
          { length: url.searchParams.get("offset") === "0" ? 100 : 1 },
          (_, index) => ({ id: `${url.searchParams.get("offset")}-${index}` }),
        ),
      ),
      { headers: { "Content-Type": "application/json" } },
    );
  });
  expect(
    await inventoryApi("http://api.test").allocations(undefined, "component"),
  ).toHaveLength(101);
  expect(urls.map((url) => url.searchParams.get("offset"))).toEqual([
    "0",
    "100",
  ]);
  expect(
    urls.every(
      (url) => url.searchParams.get("project_component_id") === "component",
    ),
  ).toBe(true);
});
test("costo ausente es desconocido; un error de servidor no se transforma en cero", async () => {
  vi.stubGlobal(
    "fetch",
    async () =>
      new Response(JSON.stringify({ detail: "No hay compra" }), {
        status: 404,
      }),
  );
  expect(await inventoryApi("http://api.test").cost("supply")).toBeNull();
  vi.stubGlobal(
    "fetch",
    async () =>
      new Response(JSON.stringify({ detail: "Temporal" }), {
        status: 503,
        headers: { "Content-Type": "application/json" },
      }),
  );
  await expect(
    inventoryApi("http://api.test").cost("supply"),
  ).rejects.toBeInstanceOf(ApiError);
});
test("fecha local conserva minutos; conversión UTC y aviso de revisión rechazan datos ilegibles", () => {
  expect(localDateTime(new Date(2026, 9, 14, 9, 30))).toBe("2026-10-14T09:30");
  expect(utcDateTime("2026-10-14T10:00:00-03:00")).toBe(
    "2026-10-14T13:00:00.000Z",
  );
  expect(() => utcDateTime("")).toThrow();
  expect(
    reviewRecord.safeParse({ version: 2, summary: "Compra" }).success,
  ).toBe(false);
});
