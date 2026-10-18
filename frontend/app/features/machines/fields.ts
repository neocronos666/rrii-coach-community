import type { Schema } from "./api";
export const machineTypes = {
  fdm_printer: "Impresora FDM",
  sla_printer: "Impresora SLA",
  cnc: "CNC",
  laser: "Láser",
  scanner: "Escáner",
  washer: "Lavadora",
  curing_station: "Estación de curado",
  paper_printer: "Impresora de papel",
  label_printer: "Impresora de etiquetas",
  plotter: "Plotter",
  vinyl_cutter: "Cortadora de vinilo",
  heat_press: "Prensa térmica",
  engraver: "Grabadora",
  other: "Otra",
} satisfies Record<Schema["MachineType"], string>;
export const optionalFields = [
  { key: "manufacturer", label: "Fabricante", type: "text" },
  { key: "model", label: "Modelo", type: "text" },
  { key: "purchase_date", label: "Fecha de compra", type: "date" },
  { key: "purchase_price", label: "Precio de compra", type: "text" },
  { key: "rated_power_w", label: "Potencia nominal (W)", type: "text" },
  {
    key: "useful_life_hours",
    label: "Vida útil estimada (horas)",
    type: "text",
  },
] as const;
export function machineChanges(
  current: Schema["MachineCreate"],
  original: Schema["MachineCreate"],
): Schema["MachineUpdate"] {
  return Object.fromEntries(
    Object.entries(current).filter(
      ([key, value]) => value !== original[key as keyof typeof original],
    ),
  );
}
