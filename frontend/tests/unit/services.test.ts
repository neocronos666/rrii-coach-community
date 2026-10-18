import { afterEach, expect, test, vi } from "vitest";
import { servicesApi } from "../../app/features/services/api";
import { ApiError } from "../../app/features/shared/http";
afterEach(() => vi.unstubAllGlobals());
test("servicios pagina conservando filtros", async () => {
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
    await servicesApi("http://api.test/api/v1").list(false, "Grabado"),
  ).toHaveLength(101);
  expect(urls.map((url) => url.searchParams.get("offset"))).toEqual([
    "0",
    "100",
  ]);
  for (const url of urls) {
    expect(url.searchParams.get("active")).toBe("false");
    expect(url.searchParams.get("search")).toBe("Grabado");
  }
});
test("preview transporta contexto literal y PATCH conserva null sin request_id", async () => {
  const requests: Request[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    requests.push(request);
    return Response.json({});
  });
  const api = servicesApi("http://api.test");
  await api.preview("id", {
    values: { quantity: "2 unidades", piece: "{product}" },
  });
  await api.update("id", { action_template: null, active: false });
  expect(await requests[0]!.json()).toEqual({
    values: { quantity: "2 unidades", piece: "{product}" },
  });
  expect(requests[0]!.url).toContain("/id/action-preview");
  expect(await requests[1]!.json()).toEqual({
    action_template: null,
    active: false,
  });
  expect(requests[1]!.method).toBe("PATCH");
});
test("preview conserva conflictos del servidor", async () => {
  vi.stubGlobal("fetch", async () =>
    Response.json({ detail: "Falta contexto" }, { status: 409 }),
  );
  await expect(
    servicesApi("http://api.test").preview("id", { values: {} }),
  ).rejects.toMatchObject({
    status: 409,
    message: "Falta contexto",
  } satisfies Partial<ApiError>);
});
