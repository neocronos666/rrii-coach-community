import createClient from "openapi-fetch";
import type { components, paths } from "~/types/api.generated";
import { allPages, ApiError, errorMessage } from "../shared/http";
export type Schema = components["schemas"];
function result<T>(r: { data?: T; error?: unknown; response: Response }): T {
  if (r.data === undefined)
    throw new ApiError(errorMessage(r.error), r.response.status);
  return r.data;
}
export function detailsApi(base: string) {
  const client = createClient<paths>({
    baseUrl: base.replace(/\/$/, "").replace(/\/api\/v1$/, ""),
  });
  return {
    async update(id: string, body: Schema["AssetUpdate"]) {
      return result(
        await client.PATCH("/api/v1/assets/{asset_id}", {
          params: { path: { asset_id: id } },
          body,
        }),
      );
    },
    async categories() {
      return allPages(async (offset) =>
        result(
          await client.GET("/api/v1/asset-categories", {
            params: { query: { offset, limit: 100 } },
          }),
        ),
      );
    },
    async createCategory(name: string) {
      return result(
        await client.POST("/api/v1/asset-categories", { body: { name } }),
      );
    },
    async renameCategory(id: string, name: string) {
      return result(
        await client.PATCH("/api/v1/asset-categories/{category_id}", {
          params: { path: { category_id: id } },
          body: { name },
        }),
      );
    },
    async deleteCategory(id: string) {
      const r = await client.DELETE("/api/v1/asset-categories/{category_id}", {
        params: { path: { category_id: id } },
      });
      if (!r.response.ok)
        throw new ApiError(errorMessage(r.error), r.response.status);
      return true;
    },
  };
}
