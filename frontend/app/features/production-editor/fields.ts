import type { Schema } from "./api";
export function taskDraft(task?: Schema["ProductionTaskRead"]) {
  return {
    title: task?.title ?? "",
    description: task?.description ?? "",
    priority: task?.priority ?? "normal",
    planned_quantity: task?.planned_quantity ?? "1",
    machine_id: task?.machine_id ?? null,
    queue_position: task?.queue_position ?? 1000,
    notes: task?.notes ?? "",
    production_parameters: JSON.stringify(
      task?.production_parameters ?? {},
      null,
      2,
    ),
  };
}
export function taskChanges(
  body: ReturnType<typeof taskDraft>,
  original: ReturnType<typeof taskDraft>,
): Schema["ProductionTaskUpdate"] {
  const changes: Schema["ProductionTaskUpdate"] = {};
  for (const key of [
    "title",
    "description",
    "priority",
    "planned_quantity",
    "machine_id",
    "queue_position",
    "notes",
  ] as const) {
    if (body[key] !== original[key])
      Object.assign(changes, {
        [key]:
          key === "description" || key === "notes"
            ? body[key] || null
            : body[key],
      });
  }
  if (body.production_parameters !== original.production_parameters)
    changes.production_parameters = parameters(body.production_parameters);
  return changes;
}
export function parameters(value: string): Record<string, unknown> {
  const parsed: unknown = JSON.parse(value);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed))
    throw new Error("Los parámetros deben ser un objeto JSON.");
  return parsed as Record<string, unknown>;
}
