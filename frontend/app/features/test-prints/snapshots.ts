import { z } from "zod";
export const stepSnapshot = z.object({
  key: z.string(),
  title: z.string(),
  kind: z.string(),
  unit: z.string(),
  depends_on: z.array(z.string()),
  instructions: z.string().nullable().optional(),
  service_action: z.string().nullable().optional(),
  service_instructions: z.string().nullable().optional(),
  resources: z.array(
    z.object({
      key: z.string(),
      name: z.string(),
      revision_number: z.number(),
      quantity_per_batch: z.string(),
    }),
  ),
  supply_inputs: z.array(
    z.object({ supply_id: z.string(), quantity_per_batch: z.string() }),
  ),
  product_inputs: z.array(
    z.object({
      product_variant_id: z.string(),
      quantity_per_batch: z.string(),
      source_step_key: z.string().nullable().optional(),
    }),
  ),
});
export type StepSnapshot = z.infer<typeof stepSnapshot>;
export function snapshotName(value: Record<string, unknown>): string {
  return typeof value.recipe_name === "string" ? value.recipe_name : "";
}
export function omittedKeys(value: Record<string, unknown>): string[] {
  const parsed = z.array(z.string()).safeParse(value.omitted_step_keys);
  return parsed.success ? parsed.data : [];
}

export const configurationSnapshot = z.object({
  selections: z.array(
    z.object({
      definition_id: z.string(),
      values: z.array(
        z.object({
          value_id: z.string(),
          quantity: z.string(),
          revision_id: z.string().nullable(),
        }),
      ),
    }),
  ),
});

// Orden visual de la receta guardada; no calcula dependencias ni habilita pasos.
export function orderedSteps<T extends { snapshot: Record<string, unknown> }>(
  steps: T[],
): T[] {
  const position = (step: T) =>
    typeof step.snapshot.position === "number" &&
    Number.isInteger(step.snapshot.position)
      ? step.snapshot.position
      : Number.MAX_SAFE_INTEGER;
  return [...steps].sort((left, right) => position(left) - position(right));
}
