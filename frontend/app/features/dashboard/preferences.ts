import { z } from "zod";
import { blockIds, type BlockId } from "./blocks";
export const dashboardKey = "rrii-coach.dashboard.v1";
const schema = z.object({
  version: z.literal(1),
  blocks: z
    .array(
      z.object({
        id: z.enum(blockIds),
        visible: z.boolean(),
        size: z.enum(["standard", "wide"]),
        view: z.enum(["list", "summary"]),
      }),
    )
    .max(30),
});
export type DashboardPreferences = z.infer<typeof schema>;
export type BlockPreference = DashboardPreferences["blocks"][number];
export function supportsSummary(id: BlockId) {
  return id === "production" || id === "quotes" || id === "machines";
}
export function defaultDashboard(): DashboardPreferences {
  return {
    version: 1,
    blocks: blockIds.map((id) => ({
      id,
      visible: id !== "machines",
      size: "standard",
      view: "list",
    })),
  };
}
export function readDashboard(
  storage: Pick<Storage, "getItem">,
): DashboardPreferences {
  try {
    const parsed = schema.safeParse(
      JSON.parse(storage.getItem(dashboardKey) ?? "null"),
    );
    if (!parsed.success) return defaultDashboard();
    const seen = new Set<BlockId>();
    const blocks = parsed.data.blocks
      .filter((block) => {
        if (seen.has(block.id)) return false;
        seen.add(block.id);
        return true;
      })
      .map((block) => ({
        ...block,
        view: supportsSummary(block.id) ? block.view : ("list" as const),
      }));
    for (const block of defaultDashboard().blocks)
      if (!seen.has(block.id)) blocks.push(block);
    return { version: 1, blocks };
  } catch {
    return defaultDashboard();
  }
}
export function moveBlock(
  preferences: DashboardPreferences,
  id: BlockId,
  offset: -1 | 1,
): DashboardPreferences {
  const blocks = preferences.blocks.map((block) => ({ ...block }));
  const index = blocks.findIndex((block) => block.id === id);
  const target = index + offset;
  if (index >= 0 && target >= 0 && target < blocks.length)
    [blocks[index], blocks[target]] = [blocks[target]!, blocks[index]!];
  return { version: 1, blocks };
}

// El menú contextual mueve entre bloques visibles; el editor conserva el orden completo.
export function moveVisibleBlock(
  preferences: DashboardPreferences,
  id: BlockId,
  offset: -1 | 1,
): DashboardPreferences {
  const visible = preferences.blocks.filter((block) => block.visible);
  const index = visible.findIndex((block) => block.id === id);
  const neighbor = visible[index + offset];
  if (index < 0 || !neighbor) return preferences;
  const blocks = preferences.blocks.map((block) => ({ ...block }));
  const source = blocks.findIndex((block) => block.id === id);
  const target = blocks.findIndex((block) => block.id === neighbor.id);
  [blocks[source], blocks[target]] = [blocks[target]!, blocks[source]!];
  return { version: 1, blocks };
}
