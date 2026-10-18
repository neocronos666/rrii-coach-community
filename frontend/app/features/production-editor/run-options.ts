import type { Schema } from "./api";
import { parameters } from "./fields";
import { utcDateTime } from "../inventory/values";
export type RunOptions = {
  startedAt: string;
  override: boolean;
  parameters: string;
};
export function startPayload(
  machine: string,
  options: RunOptions,
): Omit<Schema["RunCreate"], "request_id"> {
  return {
    ...(machine ? { machine_id: machine === "none" ? null : machine } : {}),
    ...(options.startedAt
      ? { started_at: utcDateTime(options.startedAt) }
      : {}),
    ...(options.override ? { parameters: parameters(options.parameters) } : {}),
  };
}
