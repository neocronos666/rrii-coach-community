import type { Settings } from "./api";
export const identityFields = [
  {
    key: "business_name",
    label: "Nombre del negocio",
    required: false,
    max: 255,
  },
  { key: "currency", label: "Moneda", required: true, max: 3 },
  { key: "country_code", label: "Código de país", required: true, max: 2 },
  { key: "region", label: "Región", required: false, max: 255 },
  { key: "timezone", label: "Zona horaria IANA", required: true, max: 255 },
  { key: "language", label: "Código de idioma", required: true, max: 3 },
] as const;
export const costFields = [
  { key: "electricity_price_per_kwh", label: "Electricidad por kWh" },
  { key: "design_hour_rate", label: "Diseño por hora" },
  { key: "preproduction_hour_rate", label: "Preproducción por hora" },
  { key: "postproduction_hour_rate", label: "Posproducción por hora" },
  { key: "assembly_hour_rate", label: "Ensamblado por hora" },
  { key: "support_hour_rate", label: "Soporte por hora" },
  { key: "training_hour_rate", label: "Capacitación por hora" },
  { key: "pretransport_hour_rate", label: "Pretransporte por hora" },
  { key: "default_markup_percentage", label: "Markup predeterminado (%)" },
] as const;
export const policies = {
  none: "Sin seña",
  optional: "Opcional",
  required: "Obligatoria",
} as const;
export const depositTypes = {
  fixed: "Importe fijo",
  percentage: "Porcentaje",
} as const;
export const settingsLabels = {
  ...Object.fromEntries(
    identityFields.map((field) => [field.key, field.label]),
  ),
  ...Object.fromEntries(costFields.map((field) => [field.key, field.label])),
  deposit_policy: "Política de seña",
  deposit_type: "Tipo de seña",
  deposit_value: "Valor de seña",
};
// Normalización de campos opcionales de formulario; sin cálculo ni reglas de seña.
export function settingsPayload(settings: Settings): Settings {
  const result = { ...settings };
  for (const key of [
    "business_name",
    "region",
    "deposit_value",
    ...costFields.map((field) => field.key),
  ] as const) {
    result[key] =
      result[key] === "" || result[key] === undefined ? null : result[key];
  }
  result.deposit_type ??= null;
  return result;
}
export function sameSettings(a: Settings, b: Settings) {
  const left = settingsPayload(a),
    right = settingsPayload(b);
  return (
    (Object.keys(left) as (keyof Settings)[]).every(
      (key) => left[key] === right[key],
    ) && Object.keys(left).length === Object.keys(right).length
  );
}
