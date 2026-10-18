import { afterEach, expect, test, vi } from "vitest";
import { structureApi } from "../../app/features/asset-structure/api";
afterEach(() => vi.unstubAllGlobals());
test("composición conserva revisión base, revisiones hijas y precisión textual", async () => {
  let request: Request | undefined;
  vi.stubGlobal("fetch", async (r: Request) => {
    request = r;
    return Response.json({});
  });
  const body = {
    base_revision_id: "base",
    components: [
      {
        child_asset_id: "child",
        child_revision_id: "pinned",
        quantity: "123456789.123456",
      },
    ],
    note: null,
  };
  await structureApi("http://api.test/api/v1").publish("parent", body);
  expect(await request!.json()).toEqual(body);
  expect(request!.url).toContain("/assets/parent/composition-revisions");
});
test("compatibilidades recorre páginas y retiro maneja 204 sin JSON", async () => {
  const urls: URL[] = [];
  vi.stubGlobal("fetch", async (r: Request) => {
    if (r.method === "DELETE") return new Response(null, { status: 204 });
    const url = new URL(r.url);
    urls.push(url);
    return Response.json({
      items:
        url.searchParams.get("offset") === "0"
          ? Array.from({ length: 100 }, (_, id) => ({ id }))
          : [{ id: 100 }],
      total: 101,
    });
  });
  const api = structureApi("http://api.test");
  expect(await api.compatibilities("parent")).toHaveLength(101);
  expect(urls.map((url) => url.searchParams.get("offset"))).toEqual([
    "0",
    "100",
  ]);
  expect(await api.unrelate("parent", "other")).toBe(true);
});
test("asignar familia nula no cambia otra metadata y errores conservan HTTP", async () => {
  let body: unknown;
  vi.stubGlobal("fetch", async (r: Request) => {
    body = await r.json();
    return Response.json({ detail: "Conflicto" }, { status: 409 });
  });
  await expect(
    structureApi("http://api.test").assignFamily("asset", null),
  ).rejects.toMatchObject({ status: 409 });
  expect(body).toEqual({ family_id: null });
});

test("catálogo de estructura incluye activos y archivados explícitamente", async () => {
  const flags: string[] = [];
  vi.stubGlobal("fetch", async (r: Request) => {
    const flag = new URL(r.url).searchParams.get("archived")!;
    flags.push(flag);
    return Response.json([{ id: flag }]);
  });
  expect(await structureApi("http://api.test").assets()).toHaveLength(2);
  expect(flags.sort()).toEqual(["false", "true"]);
});
