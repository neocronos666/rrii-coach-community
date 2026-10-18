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
export function commercialApi(base: string) {
  const client = createClient<paths>({
    baseUrl: base.replace(/\/$/, "").replace(/\/api\/v1$/, ""),
  });
  return {
    async update(id: string, body: Schema["QuoteUpdate"]) {
      return result(
        await client.PATCH("/api/v1/quotes/{quote_id}", {
          params: { path: { quote_id: id } },
          body,
        }),
      );
    },
    async approve(id: string) {
      return result(
        await client.POST("/api/v1/quotes/{quote_id}/approve", {
          params: { path: { quote_id: id } },
        }),
      );
    },
    async reject(id: string, body: Schema["QuoteReject"]) {
      return result(
        await client.POST("/api/v1/quotes/{quote_id}/reject", {
          params: { path: { quote_id: id } },
          body,
        }),
      );
    },
    async convert(id: string) {
      return result(
        await client.POST("/api/v1/quotes/{quote_id}/convert", {
          params: { path: { quote_id: id } },
        }),
      );
    },
    async orders() {
      return result(await client.GET("/api/v1/orders"));
    },
    async projects() {
      return result(await client.GET("/api/v1/projects"));
    },
    async order(id: string) {
      return result(
        await client.GET("/api/v1/orders/{order_id}", {
          params: { path: { order_id: id } },
        }),
      );
    },
    async project(id: string) {
      return result(
        await client.GET("/api/v1/projects/{project_id}", {
          params: { path: { project_id: id } },
        }),
      );
    },
    async cancelOrder(id: string) {
      return result(
        await client.POST("/api/v1/orders/{order_id}/cancel", {
          params: { path: { order_id: id } },
        }),
      );
    },
    async cancelProject(id: string) {
      return result(
        await client.POST("/api/v1/projects/{project_id}/cancel", {
          params: { path: { project_id: id } },
        }),
      );
    },
  };
}
export type CommercialApi = ReturnType<typeof commercialApi>;
