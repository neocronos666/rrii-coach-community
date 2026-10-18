import { describe, expect, it } from "vitest";
import {
  readAppearance,
  saveAppearance,
  resolveProfile,
  nebula,
} from "../../app/theme/skin";
describe("apariencia local", () => {
  it("inicia oscuro y recupera preferencias inválidas", () => {
    for (const value of [null, "system", "broken", "dark"])
      expect(readAppearance({ getItem: () => value })).toBe("dark");
    expect(readAppearance({ getItem: () => "light" })).toBe("light");
  });
  it("tolera almacenamiento bloqueado", () => {
    expect(
      readAppearance({
        getItem() {
          throw Error();
        },
      }),
    ).toBe("dark");
    expect(() =>
      saveAppearance(
        {
          setItem() {
            throw Error();
          },
        },
        "light",
      ),
    ).not.toThrow();
  });
  it("hereda perfiles base", () => {
    expect(resolveProfile(nebula, "touch").target).toBe(52);
  });
});
