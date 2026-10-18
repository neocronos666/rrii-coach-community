import { describe, expect, it } from "vitest";
import {
  readDevice,
  saveDevice,
  resolveDisplay,
  defaultDevice,
} from "../../app/features/preferences/device";
describe("preferencias del dispositivo", () => {
  it("recupera JSON corrupto, versiones futuras y valores inválidos", () => {
    for (const raw of [
      "{",
      "{}",
      '{"version":2,"profile":"touch","density":"compact"}',
      '{"version":1,"profile":"tv","density":"compact"}',
    ])
      expect(readDevice({ getItem: () => raw })).toEqual(defaultDevice);
  });
  it("conserva perfil y densidad válidos", () => {
    const value = {
      ...defaultDevice,
      profile: "touch" as const,
      density: "compact" as const,
    };
    let stored = "";
    expect(
      saveDevice(
        {
          setItem: (_key, raw) => {
            stored = raw;
          },
        },
        value,
      ),
    ).toBe(true);
    expect(readDevice({ getItem: () => stored })).toEqual(value);
  });
  it("no falla sin almacenamiento", () => {
    expect(
      saveDevice(
        {
          setItem() {
            throw Error();
          },
        },
        defaultDevice,
      ),
    ).toBe(false);
  });
  it("resuelve automáticamente y respeta perfiles forzados", () => {
    expect(resolveDisplay("auto", true, false)).toBe("mobile");
    expect(resolveDisplay("auto", false, true)).toBe("touch");
    expect(resolveDisplay("auto", false, false)).toBe("desktop");
    expect(resolveDisplay("mobile", false, false)).toBe("mobile");
    expect(resolveDisplay("desktop", true, true)).toBe("desktop");
  });
});
