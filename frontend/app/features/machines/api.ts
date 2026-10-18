import createClient from "openapi-fetch";
import type { components, paths } from "~/types/api.generated";
import { ApiError, errorMessage } from "../shared/http";
export type Schema = components["schemas"];
function result<T>(response: {
  data?: T;
  error?: unknown;
  response: Response;
}): T {
  if (response.data === undefined)
    throw new ApiError(errorMessage(response.error), response.response.status);
  return response.data;
}
export function machinesApi(base: string) {
  const client = createClient<paths>({
    baseUrl: base.replace(/\/$/, "").replace(/\/api\/v1$/, ""),
  });
  return {
    async list(active?: boolean, machine_type?: Schema["MachineType"]) {
      return result(
        await client.GET("/api/v1/machines", {
          params: { query: { active, machine_type } },
        }),
      );
    },
    async get(id: string) {
      return result(
        await client.GET("/api/v1/machines/{machine_id}", {
          params: { path: { machine_id: id } },
        }),
      );
    },
    async create(body: Schema["MachineCreate"]) {
      return result(await client.POST("/api/v1/machines", { body }));
    },
    async update(id: string, body: Schema["MachineUpdate"]) {
      return result(
        await client.PATCH("/api/v1/machines/{machine_id}", {
          params: { path: { machine_id: id } },
          body,
        }),
      );
    },
  };
}
