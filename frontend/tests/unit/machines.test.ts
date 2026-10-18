import { afterEach, expect, test, vi } from "vitest";
import { machinesApi } from "../../app/features/machines/api";
import { machineChanges } from "../../app/features/machines/fields";
import { ApiError } from "../../app/features/shared/http";
afterEach(() => vi.unstubAllGlobals());
test("máquinas conserva precio, potencia y fecha sin conversiones ni request_id", async () => {
  let sent: Request | undefined;
  vi.stubGlobal("fetch", async (request: Request) => {
    sent = request;
    return Response.json({ id: "machine" });
  });
  const body = {
    name: "Equipo",
    machine_type: "laser" as const,
    purchase_date: "2026-10-14",
    purchase_price: "123456789.1234",
    rated_power_w: "1234.56",
    useful_life_hours: null,
    active: false,
  };
  await machinesApi("http://api.test/api/v1").create(body);
  expect(await sent!.json()).toEqual(body);
  expect(sent!.url).toBe("http://api.test/api/v1/machines");
});
test("PATCH sólo envía diferencias, incluidos null y desactivación", async () => {
  const original = {
    name: "A",
    machine_type: "cnc" as const,
    active: true,
    purchase_price: "12.3000",
    notes: "Nota",
  };
  const current = { ...original, active: false, notes: null };
  expect(machineChanges(current, original)).toEqual({
    active: false,
    notes: null,
  });
  expect(machineChanges({ ...current, name: "B" }, current)).toEqual({
    name: "B",
  });
  expect(machineChanges(current, { ...current, name: "B" })).toEqual({
    name: "A",
  });
});
test("filtros viajan al servidor y conflictos conservan HTTP", async () => {
  let url = "";
  vi.stubGlobal("fetch", async (request: Request) => {
    url = request.url;
    return Response.json({ detail: "Límite" }, { status: 409 });
  });
  await expect(
    machinesApi("http://api.test").list(false, "laser"),
  ).rejects.toBeInstanceOf(ApiError);
  expect(url).toContain("active=false");
  expect(url).toContain("machine_type=laser");
});
