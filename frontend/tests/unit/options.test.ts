import { afterEach, expect, test, vi } from "vitest";
import { optionsApi } from "../../app/features/options/api";
afterEach(() => vi.unstubAllGlobals());
test("valores pagina con su característica y conserva filtros", async () => {
  const urls: URL[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    const url = new URL(request.url);
    urls.push(url);
    return Response.json(
      url.searchParams.get("offset") === "0"
        ? Array.from({ length: 100 }, (_, id) => ({ id }))
        : [{ id: 100 }],
    );
  });
  expect(
    await optionsApi("http://api.test/api/v1").values(
      "definition",
      false,
      "Logo",
    ),
  ).toHaveLength(101);
  expect(urls.map((url) => url.searchParams.get("offset"))).toEqual([
    "0",
    "100",
  ]);
  for (const url of urls) {
    expect(url.pathname).toBe("/api/v1/option-definitions/definition/values");
    expect(url.searchParams.get("active")).toBe("false");
    expect(url.searchParams.get("search")).toBe("Logo");
  }
});
test("PATCH de valor preserva null explícito y no inventa transacciones de stock", async () => {
  const requests: Request[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    requests.push(request);
    return Response.json({});
  });
  const api = optionsApi("http://api.test");
  await api.updateOptionValue("parent", "child", {
    family_id: null,
    supply_id: null,
    active: false,
  });
  await api.updateOptionDefinition("parent", { description: null });
  expect(requests[0]!.url).toBe(
    "http://api.test/api/v1/option-definitions/parent/values/child",
  );
  expect(await requests[0]!.json()).toEqual({
    family_id: null,
    supply_id: null,
    active: false,
  });
  expect(await requests[1]!.json()).toEqual({ description: null });
});
test("pertenencia y conflicto se conservan como errores HTTP", async () => {
  vi.stubGlobal("fetch", async () =>
    Response.json(
      { detail: "No existe la opción en esta característica" },
      { status: 404 },
    ),
  );
  await expect(
    optionsApi("http://api.test").value("wrong", "child"),
  ).rejects.toMatchObject({ status: 404 });
});
