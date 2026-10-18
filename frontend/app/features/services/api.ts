import createClient from "openapi-fetch";
import type { components, paths } from "~/types/api.generated";
import { allPages, ApiError, errorMessage } from "../shared/http";
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
export function servicesApi(base: string) {
  const client = createClient<paths>({
    baseUrl: base.replace(/\/$/, "").replace(/\/api\/v1$/, ""),
  });
  return {
    async list(active?: boolean, search?: string) {
      return allPages(async (offset) =>
        result(
          await client.GET("/api/v1/service-definitions", {
            params: { query: { active, search, offset, limit: 100 } },
          }),
        ),
      );
    },
    async get(id: string) {
      return result(
        await client.GET("/api/v1/service-definitions/{definition_id}", {
          params: { path: { definition_id: id } },
        }),
      );
    },
    async create(body: Schema["ServiceDefinitionCreate"]) {
      return result(await client.POST("/api/v1/service-definitions", { body }));
    },
    async update(id: string, body: Schema["ServiceDefinitionUpdate"]) {
      return result(
        await client.PATCH("/api/v1/service-definitions/{definition_id}", {
          params: { path: { definition_id: id } },
          body,
        }),
      );
    },
    async preview(id: string, body: Schema["ServiceActionPreviewInput"]) {
      return result(
        await client.POST(
          "/api/v1/service-definitions/{definition_id}/action-preview",
          { params: { path: { definition_id: id } }, body },
        ),
      );
    },
  };
}
