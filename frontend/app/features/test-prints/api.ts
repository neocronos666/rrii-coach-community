import createClient from "openapi-fetch";
import type { components, paths } from "~/types/api.generated";
import { ApiError, errorMessage, allPages } from "../shared/http";
export type Schema = components["schemas"];
function result<T>(r: { data?: T; error?: unknown; response: Response }): T {
  if (r.data === undefined)
    throw new ApiError(errorMessage(r.error), r.response.status);
  return r.data;
}
export function testPrintApi(base: string) {
  const client = createClient<paths>({
    baseUrl: base.replace(/\/$/, "").replace(/\/api\/v1$/, ""),
  });
  return {
    async recipes(variant: string) {
      return result(
        await client.GET("/api/v1/product-variants/{variant_id}/recipes", {
          params: { path: { variant_id: variant } },
        }),
      );
    },
    async preview(recipe: string, body: Schema["PlanPreviewCreate"]) {
      return result(
        await client.POST("/api/v1/recipes/{recipe_id}/production-preview", {
          params: { path: { recipe_id: recipe } },
          body,
        }),
      );
    },
    async machines() {
      return result(await client.GET("/api/v1/machines"));
    },
    async stockMovements(variant: string) {
      return allPages(async (offset) =>
        result(
          await client.GET(
            "/api/v1/product-variants/{variant_id}/stock-movements",
            {
              params: {
                path: { variant_id: variant },
                query: { offset, limit: 100 },
              },
            },
          ),
        ),
      );
    },
    async list(offset: number, variant?: string) {
      return result(
        await client.GET("/api/v1/test-prints", {
          params: {
            query: { offset, limit: 25, variant_id: variant || undefined },
          },
        }),
      );
    },
    async get(id: string) {
      return result(
        await client.GET("/api/v1/test-prints/{print_id}", {
          params: { path: { print_id: id } },
        }),
      );
    },
    async create(body: Schema["TestPrintCreate"]) {
      return result(await client.POST("/api/v1/test-prints", { body }));
    },
    async cancel(id: string) {
      return result(
        await client.POST("/api/v1/test-prints/{print_id}/cancel", {
          params: { path: { print_id: id } },
        }),
      );
    },
    async promote(id: string, body: Schema["TestPrintPromotion"]) {
      return result(
        await client.POST("/api/v1/test-prints/{print_id}/promote", {
          params: { path: { print_id: id } },
          body,
        }),
      );
    },
    async start(id: string, key: string, body: Schema["RunCreate"]) {
      return result(
        await client.POST("/api/v1/test-prints/{print_id}/steps/{key}/runs", {
          params: { path: { print_id: id, key } },
          body,
        }),
      );
    },
    async runs(id: string, key: string) {
      return allPages(async (offset) =>
        result(
          await client.GET("/api/v1/test-prints/{print_id}/steps/{key}/runs", {
            params: {
              path: { print_id: id, key },
              query: { offset, limit: 100 },
            },
          }),
        ),
      );
    },
    async close(id: string, body: Schema["RunClose"]) {
      return result(
        await client.POST("/api/v1/production-runs/{run_id}/close", {
          params: { path: { run_id: id } },
          body,
        }),
      );
    },
    async supplies(id: string) {
      return result(
        await client.GET(
          "/api/v1/production-runs/{run_id}/supply-consumptions",
          { params: { path: { run_id: id } } },
        ),
      );
    },
    async products(id: string) {
      return result(
        await client.GET(
          "/api/v1/production-runs/{run_id}/product-consumptions",
          { params: { path: { run_id: id } } },
        ),
      );
    },
  };
}
export type TestPrintApi = ReturnType<typeof testPrintApi>;
