import { z } from "zod";

const backendHealthSchema = z.object({
  status: z.literal("ok"),
  service: z.literal("rrii-coach-backend"),
});

export type BackendHealth = z.infer<typeof backendHealthSchema>;

export async function fetchBackendHealth(
  apiBaseUrl: string,
): Promise<BackendHealth> {
  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/health`);

  if (!response.ok) {
    throw new Error(`El backend respondió HTTP ${response.status}`);
  }

  return backendHealthSchema.parse(await response.json());
}
