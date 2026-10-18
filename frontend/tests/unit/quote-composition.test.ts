import { afterEach, describe, expect, it, vi } from "vitest";
import { compositionApi } from "../../app/features/quote-composition/api";
afterEach(() => vi.unstubAllGlobals());
describe("composición comercial", () => {
  it("conserva precisión y no envía totales calculados al crear varios ítems", async () => {
    const fetcher = vi.fn(
      async () =>
        new Response(JSON.stringify({ id: "quote" }), { status: 201 }),
    );
    vi.stubGlobal("fetch", fetcher);
    const items = [
      { cost_calculation_id: "one", description: "Uno", quantity: "1.000001" },
      { cost_calculation_id: "two", description: "Dos", quantity: "2.123456" },
    ];
    await compositionApi("http://localhost/api/v1").create({
      title: "Título",
      items,
    });
    expect(await (fetcher.mock.calls[0]![0] as Request).json()).toEqual({
      title: "Título",
      items,
    });
  });
  it("reemplaza sólo ítems y conserva el error HTTP del backend", async () => {
    let request: Request | undefined;
    vi.stubGlobal("fetch", async (value: Request) => {
      request = value;
      return new Response(JSON.stringify({ detail: "Snapshot inmutable" }), {
        status: 409,
      });
    });
    await expect(
      compositionApi("http://localhost").update("id", []),
    ).rejects.toMatchObject({ status: 409 });
    expect(await request!.json()).toEqual({ items: [] });
  });
});
