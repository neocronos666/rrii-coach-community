import { z } from "zod";
export const reviewRecord = z.object({
  version: z.literal(1),
  summary: z.string(),
  createdAt: z.string(),
});
export type ReviewRecord = z.infer<typeof reviewRecord>;
export function localDateTime(now = new Date()): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
}
export function utcDateTime(value: string): string {
  const date = new Date(value);
  if (!value || !Number.isFinite(date.getTime()))
    throw new Error("Ingresá una fecha y hora válida.");
  return date.toISOString();
}
