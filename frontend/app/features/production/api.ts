import createClient from "openapi-fetch";
import type { components, paths } from "~/types/api.generated";
import { ApiError, errorMessage } from "../shared/http";
export type Schema = components["schemas"];
export type TaskFilters = NonNullable<
  paths["/api/v1/production-tasks"]["get"]["parameters"]["query"]
>;
export type Destination = { kind: "order" | "component"; id: string };
function result<T>(r: { data?: T; error?: unknown; response: Response }): T {
  if (r.data === undefined)
    throw new ApiError(errorMessage(r.error), r.response.status);
  return r.data;
}
export function productionApi(base: string) {
  const client = createClient<paths>({
    baseUrl: base.replace(/\/$/, "").replace(/\/api\/v1$/, ""),
  });
  return {
    async create(
      destination: Destination,
      body: Schema["ProductionPlanCreate"],
    ) {
      return destination.kind === "order"
        ? result(
            await client.POST("/api/v1/orders/{order_id}/production-plans", {
              params: { path: { order_id: destination.id } },
              body,
            }),
          )
        : result(
            await client.POST(
              "/api/v1/project-components/{component_id}/production-plans",
              { params: { path: { component_id: destination.id } }, body },
            ),
          );
    },
    async plan(id: string) {
      return result(
        await client.GET("/api/v1/production-plans/{plan_id}", {
          params: { path: { plan_id: id } },
        }),
      );
    },
    async tasks(query: TaskFilters = {}) {
      return result(
        await client.GET("/api/v1/production-tasks", { params: { query } }),
      );
    },
    async task(id: string) {
      return result(
        await client.GET("/api/v1/production-tasks/{task_id}", {
          params: { path: { task_id: id } },
        }),
      );
    },
    async dependencies(id: string) {
      return result(
        await client.GET("/api/v1/production-tasks/{task_id}/dependencies", {
          params: { path: { task_id: id } },
        }),
      );
    },
    async progress(id: string) {
      return result(
        await client.GET("/api/v1/production-tasks/{task_id}/progress", {
          params: { path: { task_id: id } },
        }),
      );
    },
    async runs(id: string) {
      return result(
        await client.GET("/api/v1/production-tasks/{task_id}/runs", {
          params: { path: { task_id: id } },
        }),
      );
    },
    async start(id: string, body: Schema["RunCreate"]) {
      return result(
        await client.POST("/api/v1/production-tasks/{task_id}/runs", {
          params: { path: { task_id: id } },
          body,
        }),
      );
    },
    async action(id: string, action: "pause" | "resume" | "cancel") {
      const params = { path: { task_id: id } };
      if (action === "pause")
        return result(
          await client.POST("/api/v1/production-tasks/{task_id}/pause", {
            params,
          }),
        );
      if (action === "resume")
        return result(
          await client.POST("/api/v1/production-tasks/{task_id}/resume", {
            params,
          }),
        );
      return result(
        await client.POST("/api/v1/production-tasks/{task_id}/cancel", {
          params,
        }),
      );
    },
  };
}
