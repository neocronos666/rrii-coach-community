import { z } from "zod";
export const launcherKey = "rrii-coach.launcher.v1";
export const actionIds = ["quickQuote", "quoteOrder"] as const;
export type ActionId = (typeof actionIds)[number];
const schema = z.object({
  version: z.literal(1),
  actions: z
    .array(z.object({ id: z.enum(actionIds), visible: z.boolean() }))
    .max(20),
});
export type LauncherPreferences = z.infer<typeof schema>;
export function defaultLauncher(): LauncherPreferences {
  return {
    version: 1,
    actions: actionIds.map((id) => ({ id, visible: true })),
  };
}
export function readLauncher(
  storage: Pick<Storage, "getItem">,
): LauncherPreferences {
  try {
    const result = schema.safeParse(
      JSON.parse(storage.getItem(launcherKey) ?? "null"),
    );
    if (!result.success) return defaultLauncher();
    const seen = new Set<ActionId>();
    const actions = result.data.actions.filter((action) => {
      if (seen.has(action.id)) return false;
      seen.add(action.id);
      return true;
    });
    for (const id of actionIds)
      if (!seen.has(id)) actions.push({ id, visible: true });
    return { version: 1, actions };
  } catch {
    return defaultLauncher();
  }
}
export function moveAction(
  preferences: LauncherPreferences,
  id: ActionId,
  offset: -1 | 1,
): LauncherPreferences {
  const actions = preferences.actions.map((action) => ({ ...action }));
  const index = actions.findIndex((action) => action.id === id);
  const next = index + offset;
  if (index >= 0 && next >= 0 && next < actions.length)
    [actions[index], actions[next]] = [actions[next]!, actions[index]!];
  return { version: 1, actions };
}
