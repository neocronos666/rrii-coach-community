import { z } from "zod";
export type MutationRequest = { request_id: string };
const envelope = z.object({
  version: z.literal(1),
  body: z.object({ request_id: z.uuid() }).passthrough(),
});
// Sólo solicitudes en vuelo; el historial de negocio pertenece al backend.
export function readPending<T extends MutationRequest>(
  storage: Pick<Storage, "getItem">,
  key: string,
): T | null {
  const raw = storage.getItem(key);
  if (raw === null) return null;
  return envelope.parse(JSON.parse(raw)).body as T;
}
export function savePending(
  storage: Pick<Storage, "setItem">,
  key: string,
  body: MutationRequest,
) {
  storage.setItem(key, JSON.stringify({ version: 1, body }));
}

// getRandomValues también está disponible en instalaciones HTTP de red local.
export function newRequestId(
  source: Pick<Crypto, "getRandomValues" | "randomUUID"> = crypto,
): string {
  if (typeof source.randomUUID === "function") return source.randomUUID();
  const bytes = source.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6]! & 0x0f) | 0x40;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
