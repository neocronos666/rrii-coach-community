import { afterEach, expect, test, vi } from "vitest";
import { detailsApi, type Schema } from "../../app/features/asset-details/api";
import {
  assetDraft,
  assetChanges,
} from "../../app/features/asset-details/fields";
afterEach(() => vi.unstubAllGlobals());
const asset = {
  id: "asset",
  code: "A",
  name: "Original",
  description: "Texto",
  category_id: "category",
  family_id: "family",
  current_revision_id: "revision",
  archived: false,
  third_party: true,
  author: "Autor",
  origin: null,
  license: null,
  source_url: null,
  usage_notes: null,
  created_at: "date",
  updated_at: "date",
} satisfies Schema["AssetRead"];
test("metadata proyecta sólo campos editables y PATCH retira opcionales explícitamente", () => {
  const original = assetDraft(asset),
    current = { ...original, name: "Nuevo", description: "", family_id: null };
  expect(assetChanges(current, original)).toEqual({
    name: "Nuevo",
    description: null,
    family_id: null,
  });
  expect(original).not.toHaveProperty("current_revision_id");
  expect(original).not.toHaveProperty("id");
  expect(assetChanges(original, { ...original, name: "Nuevo" })).toEqual({
    name: "Original",
  });
});
test("metadata conserva URL literal y categorías usan DELETE 204 sin cuerpo", async () => {
  const requests: Request[] = [];
  vi.stubGlobal("fetch", async (r: Request) => {
    requests.push(r);
    return r.method === "DELETE"
      ? new Response(null, { status: 204 })
      : Response.json({});
  });
  const api = detailsApi("http://api.test/api/v1");
  await api.update("asset", {
    source_url: "https://example.org/design?ref=1",
    author: null,
  });
  await api.deleteCategory("category");
  expect(await requests[0]!.json()).toEqual({
    source_url: "https://example.org/design?ref=1",
    author: null,
  });
  expect(requests[1]!.method).toBe("DELETE");
  expect(await requests[1]!.text()).toBe("");
});
test("categorías pagina y conserva conflictos del sistema", async () => {
  vi.stubGlobal("fetch", async (r: Request) => {
    if (r.method === "PATCH")
      return Response.json({ detail: "Protegida" }, { status: 409 });
    return Response.json(
      new URL(r.url).searchParams.get("offset") === "0"
        ? Array.from({ length: 100 }, (_, id) => ({ id }))
        : [{ id: 100 }],
    );
  });
  const api = detailsApi("http://api.test");
  expect(await api.categories()).toHaveLength(101);
  await expect(api.renameCategory("system", "Nuevo")).rejects.toMatchObject({
    status: 409,
  });
});
