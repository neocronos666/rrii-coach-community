import { afterEach, expect, test, vi } from "vitest";
import {
  newDefinition,
  quickQuoteApi,
  QuoteApiError,
} from "../../app/features/quick-quotes/api";
import {
  readPending,
  savePending,
  newRequestId,
} from "../../app/features/quick-quotes/pending";
afterEach(() => vi.unstubAllGlobals());
test("sólo 404 significa ausencia de formalización; otros errores conservan su estado", async () => {
  let status = 404;
  vi.stubGlobal(
    "fetch",
    async () =>
      new Response(JSON.stringify({ detail: "No disponible" }), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
  );
  const api = quickQuoteApi("http://api.test/api/v1");
  expect(await api.formalization("draft")).toBeNull();
  for (status of [409, 422, 500]) {
    await expect(api.formalization("draft")).rejects.toMatchObject({
      status,
      message: "No disponible",
    });
    await expect(api.formalization("draft")).rejects.toBeInstanceOf(
      QuoteApiError,
    );
  }
});
test("preview conserva precisión, cero explícito y selecciones vacías sin calcular importes", async () => {
  const bodies: unknown[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    bodies.push(await request.json());
    return new Response("{}", {
      headers: { "Content-Type": "application/json" },
    });
  });
  const api = quickQuoteApi("http://api.test/api/v1/"),
    pricing = newDefinition().pricing;
  pricing.target_quantity = "123456789012.123456";
  pricing.step_estimates = {
    final: {
      extras: [
        { description: "Extra", amount: "999999999.9999", currency: "ARS" },
      ],
    },
  };
  await api.preview(pricing);
  await api.preview({
    ...pricing,
    markup_percentage: "0",
    selections: [{ definition_id: "option", values: [] }],
  });
  expect(bodies[0]).toMatchObject({
    target_quantity: "123456789012.123456",
    markup_percentage: null,
    selections: [],
    step_estimates: pricing.step_estimates,
  });
  expect(bodies[1]).toMatchObject({
    markup_percentage: "0",
    selections: [{ definition_id: "option", values: [] }],
  });
});
test("historial recorre todas las páginas sin limitarse a cien revisiones", async () => {
  const offsets: string[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    const offset = new URL(request.url).searchParams.get("offset")!;
    offsets.push(offset);
    return new Response(
      JSON.stringify(
        offset === "0"
          ? Array.from({ length: 100 }, (_, i) => ({ revision: 101 - i }))
          : [{ revision: 1 }],
      ),
      { headers: { "Content-Type": "application/json" } },
    );
  });
  expect(await quickQuoteApi("http://api.test").history("draft")).toHaveLength(
    101,
  );
  expect(offsets).toEqual(["0", "100"]);
});
test("solicitud pendiente conserva identidad, revisión y decimales después de recargar", () => {
  const values = new Map<string, string>();
  const storage = {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => {
      values.set(key, value);
    },
  };
  const body = {
    request_id: "eb05c74b-1bf0-4aa7-9235-bf3128b20e01",
    expected_revision: 7,
    ...newDefinition(),
  };
  body.pricing.markup_percentage = "0";
  body.pricing.target_quantity = "0.000001";
  expect(readPending(storage, "pending")).toBeNull();
  savePending(storage, "pending", body);
  expect(readPending(storage, "pending")).toEqual(body);
  for (const invalid of [
    "{",
    JSON.stringify({ version: 2, body }),
    JSON.stringify({ version: 1, body: { request_id: "invalid" } }),
  ]) {
    storage.setItem("pending", invalid);
    expect(() => readPending(storage, "pending")).toThrow();
  }
});

test("UUID válido también sin randomUUID en HTTP local", () => {
  const source = {
    getRandomValues: crypto.getRandomValues.bind(crypto),
    randomUUID: undefined,
  } as unknown as Crypto;
  const id = newRequestId(source);
  expect(id).toMatch(
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
  );
  expect(newRequestId(source)).not.toBe(id);
});
