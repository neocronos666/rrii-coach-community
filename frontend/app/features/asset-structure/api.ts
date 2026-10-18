import createClient from "openapi-fetch";
import type { components, paths } from "~/types/api.generated";
import { allPages, ApiError, errorMessage } from "../shared/http";
export type Schema = components["schemas"];
function result<T>(r: { data?: T; error?: unknown; response: Response }): T {
  if (r.data === undefined)
    throw new ApiError(errorMessage(r.error), r.response.status);
  return r.data;
}
export function structureApi(base: string) {
  const client = createClient<paths>({
    baseUrl: base.replace(/\/$/, "").replace(/\/api\/v1$/, ""),
  });
  return {
    async assets() {
      const pages = await Promise.all(
        [false, true].map((archived) =>
          allPages(async (offset) =>
            result(
              await client.GET("/api/v1/assets", {
                params: { query: { archived, offset, limit: 100 } },
              }),
            ),
          ),
        ),
      );
      return pages.flat();
    },
    async families() {
      return allPages(async (offset) =>
        result(
          await client.GET("/api/v1/asset-families", {
            params: { query: { offset, limit: 100 } },
          }),
        ),
      );
    },
    async family(id: string) {
      return result(
        await client.GET("/api/v1/asset-families/{family_id}", {
          params: { path: { family_id: id } },
        }),
      );
    },
    async createFamily(body: Schema["FamilyCreate"]) {
      return result(await client.POST("/api/v1/asset-families", { body }));
    },
    async updateFamily(id: string, body: Schema["FamilyUpdate"]) {
      return result(
        await client.PATCH("/api/v1/asset-families/{family_id}", {
          params: { path: { family_id: id } },
          body,
        }),
      );
    },
    async assignFamily(asset: string, family: string | null) {
      return result(
        await client.PATCH("/api/v1/assets/{asset_id}", {
          params: { path: { asset_id: asset } },
          body: { family_id: family },
        }),
      );
    },
    async composition(asset: string, revision: string) {
      return result(
        await client.GET(
          "/api/v1/assets/{asset_id}/revisions/{revision_id}/composition",
          { params: { path: { asset_id: asset, revision_id: revision } } },
        ),
      );
    },
    async updates(asset: string, revision: string) {
      return result(
        await client.GET(
          "/api/v1/assets/{asset_id}/revisions/{revision_id}/component-updates",
          { params: { path: { asset_id: asset, revision_id: revision } } },
        ),
      );
    },
    async publish(asset: string, body: Schema["CompositionRevisionCreate"]) {
      return result(
        await client.POST("/api/v1/assets/{asset_id}/composition-revisions", {
          params: { path: { asset_id: asset } },
          body,
        }),
      );
    },
    async compatibilities(asset: string) {
      const rows: Schema["RelatedAssetRead"][] = [];
      for (let offset = 0; ; offset += 100) {
        const page = result(
          await client.GET("/api/v1/assets/{asset_id}/compatibilities", {
            params: {
              path: { asset_id: asset },
              query: { offset, limit: 100 },
            },
          }),
        );
        rows.push(...page.items);
        if (page.items.length < 100) return rows;
      }
    },
    async relate(asset: string, other: string) {
      return result(
        await client.PUT(
          "/api/v1/assets/{asset_id}/compatibilities/{other_id}",
          { params: { path: { asset_id: asset, other_id: other } } },
        ),
      );
    },
    async unrelate(asset: string, other: string) {
      const r = await client.DELETE(
        "/api/v1/assets/{asset_id}/compatibilities/{other_id}",
        { params: { path: { asset_id: asset, other_id: other } } },
      );
      if (!r.response.ok)
        throw new ApiError(errorMessage(r.error), r.response.status);
      return true;
    },
  };
}
