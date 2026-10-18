import { afterEach, expect, test, vi } from "vitest";
import { commercialApi } from "../../app/features/commercial/api";
import { quotePatch } from "../../app/features/commercial/drafts";
import { ApiError } from "../../app/features/shared/http";
afterEach(() => vi.unstubAllGlobals());
test("edición textual omite economía; null explícito restituye precio sugerido", () => {
  const original = {
    title: "Oferta",
    description: "Texto",
    notes: "",
    valid_until: "",
    markup_percentage: "12.3456",
    final_price: "123456789.1234",
    manual: true,
    adjustments: [],
  };
  expect(
    quotePatch(
      { ...original, title: "Revisada", description: "" },
      original,
      false,
    ),
  ).toEqual({ title: "Revisada", description: null });
  expect(quotePatch({ ...original, manual: false }, original, true)).toEqual({
    markup_percentage: "12.3456",
    final_price: null,
    adjustments: [],
  });
  expect(quotePatch(original, original, false)).toEqual({});
});
test("contratos comerciales conservan Decimal textual y conversión sin cuerpo artificial", async () => {
  const requests: Request[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    requests.push(request);
    return new Response("{}", {
      headers: { "Content-Type": "application/json" },
    });
  });
  const api = commercialApi("http://api.test/api/v1");
  await api.update("quote", {
    final_price: "123456789.1234",
    markup_percentage: "0.0001",
  });
  await api.approve("quote");
  await api.reject("quote", { reason: "No aceptado" });
  await api.convert("quote");
  await api.cancelOrder("order");
  await api.cancelProject("project");
  expect(await requests[0]!.json()).toEqual({
    final_price: "123456789.1234",
    markup_percentage: "0.0001",
  });
  expect(await requests[1]!.text()).toBe("");
  expect(await requests[2]!.json()).toEqual({ reason: "No aceptado" });
  expect(requests[3]!.url).toBe("http://api.test/api/v1/quotes/quote/convert");
  expect(await requests[3]!.text()).toBe("");
});
test("conflictos mantienen código HTTP y mensaje del servidor", async () => {
  vi.stubGlobal(
    "fetch",
    async () =>
      new Response(JSON.stringify({ detail: "No editable" }), {
        status: 409,
        headers: { "Content-Type": "application/json" },
      }),
  );
  await expect(
    commercialApi("http://api.test").update("id", { title: "Otro" }),
  ).rejects.toBeInstanceOf(ApiError);
  await expect(
    commercialApi("http://api.test").approve("id"),
  ).rejects.toMatchObject({ status: 409, message: "No editable" });
});
