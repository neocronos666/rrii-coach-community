import createClient from "openapi-fetch";
import type { components, paths } from "~/types/api.generated";

export type Asset = components["schemas"]["AssetRead"];
export type Revision = components["schemas"]["RevisionRead"];
export type Attachment = components["schemas"]["RevisionFileRead"];
export type FileRole = components["schemas"]["FileRole"];

export { errorMessage } from "../shared/http";
import { unwrap } from "../shared/http";

export function assetApi(baseUrl: string) {
  const base = baseUrl.replace(/\/$/, "");
  const client = createClient<paths>({
    baseUrl: base.replace(/\/api\/v1$/, ""),
  });
  const revisionPath = (assetId: string, revisionId: string) => ({
    asset_id: assetId,
    revision_id: revisionId,
  });
  return {
    async list(search: string, archived: boolean, offset: number) {
      return unwrap(
        await client.GET("/api/v1/assets", {
          params: {
            query: { search: search || undefined, archived, offset, limit: 25 },
          },
        }),
      );
    },
    async categories() {
      const rows: components["schemas"]["CategoryRead"][] = [];
      for (let offset = 0; ; offset += 100) {
        const page = unwrap(
          await client.GET("/api/v1/asset-categories", {
            params: { query: { offset, limit: 100 } },
          }),
        );
        rows.push(...page);
        if (page.length < 100) return rows;
      }
    },
    async create(body: components["schemas"]["AssetCreate"]) {
      return unwrap(await client.POST("/api/v1/assets", { body }));
    },
    async get(id: string) {
      return unwrap(
        await client.GET("/api/v1/assets/{asset_id}", {
          params: { path: { asset_id: id } },
        }),
      );
    },
    async archive(id: string, archived: boolean) {
      return unwrap(
        await client.PATCH("/api/v1/assets/{asset_id}", {
          params: { path: { asset_id: id } },
          body: { archived },
        }),
      );
    },
    async revisions(id: string) {
      const rows: Revision[] = [];
      for (let offset = 0; ; offset += 100) {
        const page = unwrap(
          await client.GET("/api/v1/assets/{asset_id}/revisions", {
            params: { path: { asset_id: id }, query: { offset, limit: 100 } },
          }),
        );
        rows.push(...page);
        if (page.length < 100) return rows;
      }
    },
    async newRevision(id: string, note: string) {
      return unwrap(
        await client.POST("/api/v1/assets/{asset_id}/revisions", {
          params: { path: { asset_id: id } },
          body: { note: note || null },
        }),
      );
    },
    async restore(id: string, revision: string, note: string) {
      return unwrap(
        await client.POST(
          "/api/v1/assets/{asset_id}/revisions/{revision_id}/restore",
          {
            params: { path: revisionPath(id, revision) },
            body: { note: note || null },
          },
        ),
      );
    },
    async files(id: string, revision: string) {
      return unwrap(
        await client.GET(
          "/api/v1/assets/{asset_id}/revisions/{revision_id}/files",
          { params: { path: revisionPath(id, revision) } },
        ),
      );
    },
    async upload(
      id: string,
      revision: string,
      file: File,
      filename: string,
      role: FileRole,
    ) {
      return unwrap(
        await client.POST(
          "/api/v1/assets/{asset_id}/revisions/{revision_id}/files",
          {
            params: {
              path: revisionPath(id, revision),
              query: { filename, role },
            },
            headers: { "Content-Type": "application/octet-stream" },
            bodySerializer: () => file,
            body: "",
          },
        ),
      );
    },
    async compare(id: string, revision: string, other: string) {
      return unwrap(
        await client.GET(
          "/api/v1/assets/{asset_id}/revisions/{revision_id}/files-diff/{other_revision_id}",
          {
            params: {
              path: { ...revisionPath(id, revision), other_revision_id: other },
            },
          },
        ),
      );
    },
    thumbnail(id: string, revision: string) {
      return `${base}/assets/${encodeURIComponent(id)}/revisions/${encodeURIComponent(revision)}/thumbnail`;
    },
    download(id: string, revision: string, attachment: string) {
      return `${base}/assets/${encodeURIComponent(id)}/revisions/${encodeURIComponent(revision)}/files/${encodeURIComponent(attachment)}/content`;
    },
  };
}
