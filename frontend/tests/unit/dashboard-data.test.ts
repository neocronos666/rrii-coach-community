import { afterEach, expect, test, vi } from "vitest";
import {
  dashboardApi,
  latest,
  quoteRow,
} from "../../app/features/dashboard/data";
import type { Schema } from "../../app/features/production/api";
afterEach(() => vi.unstubAllGlobals());
test("proyección comercial conserva importe textual sin sumar monedas", () => {
  const row = {
    id: "q",
    code: "Q-1",
    title: "Título",
    status: "draft",
    updated_at: "2026-01-01T00:00:00Z",
    currency: "ARS",
    breakdown: { final_price: "999999999999.0001" },
  } as Schema["QuoteRead"];
  expect(quoteRow(row).amount).toBe("ARS 999999999999.0001");
  const rows = [
    quoteRow(row),
    { ...quoteRow(row), id: "new", updated: "2026-02-01T00:00:00Z" },
  ];
  expect(latest(rows)[0]?.id).toBe("new");
  expect(rows[0]?.id).toBe("q");
});
test("una API caída propaga el error y no retorna una lista vacía", async () => {
  vi.stubGlobal(
    "fetch",
    async () =>
      new Response(JSON.stringify({ detail: "No disponible" }), {
        status: 503,
      }),
  );
  await expect(
    dashboardApi("http://api.test").load("production"),
  ).rejects.toMatchObject({ status: 503 });
});
