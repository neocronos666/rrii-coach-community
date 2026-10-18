import { afterEach, expect, test, vi } from "vitest";
import { assetApi, errorMessage } from "../../app/features/assets/api";

afterEach(() => vi.unstubAllGlobals());

test("carga bytes sin convertir el archivo a JSON y conserva errores de API", async () => {
  const requests: Request[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    requests.push(request);
    return new Response(
      JSON.stringify({ detail: "La revisión ya tiene miniatura" }),
      { status: 409, headers: { "Content-Type": "application/json" } },
    );
  });
  const api = assetApi("http://api.test/api/v1");
  const file = new File([new Uint8Array([0, 255, 10, 20])], "imagen.png");
  await expect(
    api.upload("asset", "revision", file, "vista #1.png", "thumbnail"),
  ).rejects.toThrow("La revisión ya tiene miniatura");
  expect(requests[0]!.url).toContain(
    "/api/v1/assets/asset/revisions/revision/files?",
  );
  expect(new URL(requests[0]!.url).searchParams.get("filename")).toBe(
    "vista #1.png",
  );
  expect(requests[0]!.headers.get("content-type")).toBe(
    "application/octet-stream",
  );
  expect([...new Uint8Array(await requests[0]!.arrayBuffer())]).toEqual([
    0, 255, 10, 20,
  ]);
});

test("los filtros se envían al backend y las revisiones no se truncan a 100", async () => {
  const urls: URL[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    const url = new URL(request.url);
    urls.push(url);
    const rows =
      url.pathname.endsWith("/revisions") &&
      url.searchParams.get("offset") === "0"
        ? Array.from({ length: 100 }, (_, number) => ({ id: String(number) }))
        : [];
    return new Response(JSON.stringify(rows), {
      headers: { "Content-Type": "application/json" },
    });
  });
  const api = assetApi("http://api.test/api/v1/");
  await api.list("pieza azul", true, 24);
  expect(urls[0]!.searchParams.get("search")).toBe("pieza azul");
  expect(urls[0]!.searchParams.get("archived")).toBe("true");
  expect(urls[0]!.searchParams.get("offset")).toBe("24");
  expect(await api.revisions("asset")).toHaveLength(100);
  expect(urls.at(-1)!.searchParams.get("offset")).toBe("100");
});

test("errores de validación y conexión son legibles", () => {
  expect(errorMessage({ detail: [{ msg: "Nombre obligatorio" }] })).toBe(
    "Nombre obligatorio",
  );
  expect(errorMessage(new TypeError("Failed to fetch"))).toContain("conexión");
  expect(errorMessage({ detail: [{ arbitrary: true }] })).not.toContain(
    "[object Object]",
  );
});
