import createClient from "openapi-fetch";
import type { components, paths } from "~/types/api.generated";
import type { Destination } from "../production/api";
import { ApiError, errorMessage } from "../shared/http";
export type Schema = components["schemas"];
function result<T>(r: { data?: T; error?: unknown; response: Response }): T {
  if (r.data === undefined)
    throw new ApiError(errorMessage(r.error), r.response.status);
  return r.data;
}
export function taskEditorApi(base: string) {
  const client = createClient<paths>({
    baseUrl: base.replace(/\/$/, "").replace(/\/api\/v1$/, ""),
  });
  return {
    async create(
      destination: Destination,
      body: Schema["ProductionTaskCreate"],
    ) {
      return destination.kind === "order"
        ? result(
            await client.POST("/api/v1/orders/{order_id}/production-tasks", {
              params: { path: { order_id: destination.id } },
              body,
            }),
          )
        : result(
            await client.POST(
              "/api/v1/project-components/{component_id}/production-tasks",
              { params: { path: { component_id: destination.id } }, body },
            ),
          );
    },
    async update(id: string, body: Schema["ProductionTaskUpdate"]) {
      return result(
        await client.PATCH("/api/v1/production-tasks/{task_id}", {
          params: { path: { task_id: id } },
          body,
        }),
      );
    },
    async addDependency(id: string, prerequisite: string) {
      return result(
        await client.POST("/api/v1/production-tasks/{task_id}/dependencies", {
          params: { path: { task_id: id } },
          body: { depends_on_task_id: prerequisite },
        }),
      );
    },
    async removeDependency(id: string, prerequisite: string) {
      const r = await client.DELETE(
        "/api/v1/production-tasks/{task_id}/dependencies/{depends_on_task_id}",
        { params: { path: { task_id: id, depends_on_task_id: prerequisite } } },
      );
      if (!r.response.ok)
        throw new ApiError(errorMessage(r.error), r.response.status);
      return true;
    },
    async legacy(id: string, action: "start" | "finish") {
      return action === "start"
        ? result(
            await client.POST("/api/v1/production-tasks/{task_id}/start", {
              params: { path: { task_id: id } },
            }),
          )
        : result(
            await client.POST("/api/v1/production-tasks/{task_id}/finish", {
              params: { path: { task_id: id } },
            }),
          );
    },
  };
}
