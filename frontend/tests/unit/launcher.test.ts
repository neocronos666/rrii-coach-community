import { describe, expect, it } from "vitest";
import {
  defaultLauncher,
  readLauncher,
  moveAction,
} from "../../app/features/launcher/preferences";
describe("launcher", () => {
  it("restaura defaults ante corrupción", () => {
    expect(readLauncher({ getItem: () => "{" })).toEqual(defaultLauncher());
  });
  it("normaliza duplicados y recupera acciones faltantes", () => {
    const raw = JSON.stringify({
      version: 1,
      actions: [
        { id: "quoteOrder", visible: false },
        { id: "quoteOrder", visible: true },
      ],
    });
    expect(readLauncher({ getItem: () => raw }).actions).toEqual([
      { id: "quoteOrder", visible: false },
      { id: "quickQuote", visible: true },
    ]);
  });
  it("reordena sin mutar y respeta límites", () => {
    const initial = defaultLauncher();
    expect(moveAction(initial, "quickQuote", -1)).toEqual(initial);
    expect(moveAction(initial, "quickQuote", 1).actions[0]!.id).toBe(
      "quoteOrder",
    );
    expect(initial.actions[0]!.id).toBe("quickQuote");
  });
});
