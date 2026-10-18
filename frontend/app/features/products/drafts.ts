import type { Schema, Step } from "./api";
export const units: Schema["SupplyUnit"][] = [
  "unit",
  "g",
  "kg",
  "ml",
  "l",
  "mm",
  "cm",
  "m",
  "m2",
  "m3",
];
export const taskTypes: Schema["ProductionTaskType"][] = [
  "manual",
  "fdm_print",
  "sla_print",
  "assembly",
  "postprocessing",
  "cnc",
  "laser",
  "other",
];
export const machineTypes: Schema["MachineType"][] = [
  "fdm_printer",
  "sla_printer",
  "cnc",
  "laser",
  "scanner",
  "washer",
  "curing_station",
  "paper_printer",
  "label_printer",
  "plotter",
  "vinyl_cutter",
  "heat_press",
  "engraver",
  "other",
];
export function newVariant(): Schema["VariantCreate"] {
  return {
    name: "",
    sku: null,
    description: null,
    base_unit: "unit",
    attributes: {},
    active: true,
  };
}
export function newStep(key: string): Step {
  return {
    key,
    title: "",
    kind: "operation",
    task_type: "manual",
    unit: "unit",
    quantity_per_output: "1",
    batch_yield: "1",
    is_final_output: false,
    scale_by_selection: false,
    action_context: {},
    parameters: {},
    resources: [],
    supply_inputs: [],
    selected_supply_inputs: [],
    product_inputs: [],
    depends_on: [],
  };
}
// Proyectar sólo campos de escritura: no enviar identidad ni metadatos resueltos.
export function stepDraft(row: Schema["StepRead"]): Step {
  return structuredClone({
    key: row.key,
    title: row.title,
    kind: row.kind,
    task_type: row.task_type,
    unit: row.unit,
    quantity_per_output: row.quantity_per_output,
    batch_yield: row.batch_yield,
    is_final_output: row.is_final_output,
    scale_by_selection: row.scale_by_selection,
    when_selected: row.when_selected,
    service_definition_id: row.service_definition_id,
    action_template: row.action_template,
    action_context: row.action_context ?? {},
    output_variant_id: row.output_variant_id,
    required_machine_type: row.required_machine_type,
    instructions: row.instructions,
    parameters: row.parameters ?? {},
    supply_inputs: row.supply_inputs ?? [],
    selected_supply_inputs: row.selected_supply_inputs ?? [],
    product_inputs: row.product_inputs ?? [],
    depends_on: row.depends_on ?? [],
    resources: (row.resources ?? []).map((resource) =>
      "from_selection" in resource
        ? resource
        : {
            key: resource.key,
            asset_revision_id: resource.asset_revision_id,
            quantity_per_batch: resource.quantity_per_batch,
            label: resource.label,
          },
    ),
  });
}
export function variantUpdate(
  row: Schema["VariantRead"],
): Schema["VariantUpdate"] {
  return {
    name: row.name,
    description: row.description,
    sku: row.sku,
    active: row.active,
    attributes: { ...row.attributes },
  };
}
