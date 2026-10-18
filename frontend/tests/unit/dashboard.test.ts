import { describe, expect, it } from "vitest";
import {
  defaultDashboard,
  readDashboard,
  moveBlock,
  moveVisibleBlock,
} from "../../app/features/dashboard/preferences";
describe("dashboard configurable", () => {
  it("inicia con cuatro bloques y máquinas ocultas", () => {
    const initial = defaultDashboard();
    expect(
      initial.blocks.filter((block) => block.visible).map((block) => block.id),
    ).toEqual(["production", "quotes", "attention", "activity"]);
  });
  it("recupera corrupción y versiones incompatibles", () => {
    for (const raw of ["broken", '{"version":2,"blocks":[]}'])
      expect(readDashboard({ getItem: () => raw })).toEqual(defaultDashboard());
  });
  it("deduplica, incorpora bloques faltantes y normaliza vistas incompatibles", () => {
    const block = {
      id: "attention",
      visible: false,
      size: "wide",
      view: "summary",
    };
    const raw = JSON.stringify({ version: 1, blocks: [block, block] });
    const parsed = readDashboard({ getItem: () => raw });
    expect(parsed.blocks).toHaveLength(5);
    expect(parsed.blocks[0]).toEqual({ ...block, view: "list" });
  });
  it("reordena sin mutar ni salir de límites", () => {
    const initial = defaultDashboard();
    expect(moveBlock(initial, "production", -1)).toEqual(initial);
    expect(moveBlock(initial, "quotes", -1).blocks[0]!.id).toBe("quotes");
    expect(initial.blocks[0]!.id).toBe("production");
  });
});

it("el movimiento contextual salta bloques ocultos y respeta el último visible", () => {
  const initial = defaultDashboard();
  expect(moveVisibleBlock(initial, "activity", 1)).toEqual(initial);
  initial.blocks[1]!.visible = false;
  const moved = moveVisibleBlock(initial, "production", 1);
  expect(
    moved.blocks.filter((block) => block.visible).map((block) => block.id),
  ).toEqual(["attention", "production", "activity"]);
  expect(moved.blocks[1]!.visible).toBe(false);
});
