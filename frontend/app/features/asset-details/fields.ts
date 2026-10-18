import type { Schema } from "./api";
export const textFields = [
  { key: "name", label: "Nombre", required: true, max: 255 },
  { key: "description", label: "Descripción", required: false, max: 10000 },
  { key: "author", label: "Autor", required: false, max: 255 },
  { key: "origin", label: "Origen", required: false, max: 255 },
  { key: "license", label: "Licencia", required: false, max: 255 },
  { key: "source_url", label: "URL de origen", required: false, max: 2048 },
  { key: "usage_notes", label: "Notas de uso", required: false, max: 10000 },
] as const;
export function assetDraft(row: Schema["AssetRead"]) {
  return {
    name: row.name,
    description: row.description,
    category_id: row.category_id,
    family_id: row.family_id,
    third_party: row.third_party,
    author: row.author,
    origin: row.origin,
    license: row.license,
    source_url: row.source_url,
    usage_notes: row.usage_notes,
    archived: row.archived,
  };
}
export type AssetDraft = ReturnType<typeof assetDraft>;
export function normalizedDraft(row: AssetDraft): AssetDraft {
  return {
    ...row,
    description: row.description || null,
    author: row.author || null,
    origin: row.origin || null,
    license: row.license || null,
    source_url: row.source_url || null,
    usage_notes: row.usage_notes || null,
  };
}
export function assetChanges(
  row: AssetDraft,
  original: AssetDraft,
): Schema["AssetUpdate"] {
  const payload = normalizedDraft(row);
  return Object.fromEntries(
    Object.entries(payload).filter(
      ([key, value]) => value !== original[key as keyof AssetDraft],
    ),
  );
}
