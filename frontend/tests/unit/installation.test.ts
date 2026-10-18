import { afterEach, expect, test, vi } from "vitest";
import {
  installationApi,
  type Settings,
} from "../../app/features/installation/api";
import {
  settingsPayload,
  sameSettings,
  identityFields,
  costFields,
} from "../../app/features/installation/fields";
const initial: Settings = {
  currency: "ARS",
  country_code: "AR",
  timezone: "America/Argentina/Buenos_Aires",
  language: "es",
  deposit_policy: "none",
};
afterEach(() => vi.unstubAllGlobals());
test("configuración envía PUT completo y conserva precisión, sin request_id", async () => {
  let sent: Request | undefined;
  vi.stubGlobal("fetch", async (request: Request) => {
    sent = request;
    return Response.json(initial);
  });
  const payload = settingsPayload({
    ...initial,
    design_hour_rate: "123456789.1234",
    support_hour_rate: "0",
    electricity_price_per_kwh: "",
  });
  await installationApi("http://api.test/api/v1").save(payload);
  expect(sent!.method).toBe("PUT");
  expect(sent!.url).toBe("http://api.test/api/v1/settings");
  expect(await sent!.json()).toEqual(payload);
  expect(payload.design_hour_rate).toBe("123456789.1234");
  expect(payload.support_hour_rate).toBe("0");
  expect(payload.electricity_price_per_kwh).toBeNull();
  expect(Object.keys(payload)).toHaveLength(
    identityFields.length + costFields.length + 3,
  );
});
test("comparación ignora orden, pero detecta cambios y no confunde cero con desconocido", () => {
  expect(sameSettings(initial, { ...initial })).toBe(true);
  expect(sameSettings(initial, { ...initial, business_name: "Otro" })).toBe(
    false,
  );
  expect(sameSettings(initial, { ...initial, design_hour_rate: "0" })).toBe(
    false,
  );
  expect(
    sameSettings(initial, {
      deposit_policy: "none",
      language: "es",
      timezone: initial.timezone,
      country_code: "AR",
      currency: "ARS",
    }),
  ).toBe(true);
});
test("no corrige reglas de seña en frontend ni modifica el objeto leído", () => {
  const current = {
    ...initial,
    deposit_value: "120.1234",
    deposit_type: "percentage" as const,
  };
  expect(settingsPayload(current).deposit_value).toBe("120.1234");
  expect(settingsPayload(current).deposit_type).toBe("percentage");
  expect(current).not.toHaveProperty("design_hour_rate");
});
