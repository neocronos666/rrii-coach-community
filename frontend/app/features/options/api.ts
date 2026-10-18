import createClient from "openapi-fetch";
import type { components, paths } from "~/types/api.generated";
import { allPages, ApiError, errorMessage } from "../shared/http";
export type Schema = components["schemas"];
export type OptionRecord =
  | Schema["OptionDefinitionRead"]
  | Schema["OptionValueRead"];
function result<T>(r: { data?: T; error?: unknown; response: Response }): T {
  if (r.data === undefined)
    throw new ApiError(errorMessage(r.error), r.response.status);
  return r.data;
}
export function optionsApi(base: string) {
  const client = createClient<paths>({
    baseUrl: base.replace(/\/$/, "").replace(/\/api\/v1$/, ""),
  });
  return {
    async definitions(active?: boolean, search?: string) {
      return allPages(async (offset) =>
        result(
          await client.GET("/api/v1/option-definitions", {
            params: { query: { active, search, offset, limit: 100 } },
          }),
        ),
      );
    },
    async definition(id: string) {
      return result(
        await client.GET("/api/v1/option-definitions/{definition_id}", {
          params: { path: { definition_id: id } },
        }),
      );
    },
    async createOptionDefinition(body: Schema["OptionDefinitionCreate"]) {
      return result(await client.POST("/api/v1/option-definitions", { body }));
    },
    async updateOptionDefinition(
      id: string,
      body: Schema["OptionDefinitionUpdate"],
    ) {
      return result(
        await client.PATCH("/api/v1/option-definitions/{definition_id}", {
          params: { path: { definition_id: id } },
          body,
        }),
      );
    },
    async values(definition: string, active?: boolean, search?: string) {
      return allPages(async (offset) =>
        result(
          await client.GET(
            "/api/v1/option-definitions/{definition_id}/values",
            {
              params: {
                path: { definition_id: definition },
                query: { active, search, offset, limit: 100 },
              },
            },
          ),
        ),
      );
    },
    async value(definition: string, id: string) {
      return result(
        await client.GET(
          "/api/v1/option-definitions/{definition_id}/values/{value_id}",
          { params: { path: { definition_id: definition, value_id: id } } },
        ),
      );
    },
    async createOptionValue(
      definition: string,
      body: Schema["OptionValueCreate"],
    ) {
      return result(
        await client.POST("/api/v1/option-definitions/{definition_id}/values", {
          params: { path: { definition_id: definition } },
          body,
        }),
      );
    },
    async updateOptionValue(
      definition: string,
      id: string,
      body: Schema["OptionValueUpdate"],
    ) {
      return result(
        await client.PATCH(
          "/api/v1/option-definitions/{definition_id}/values/{value_id}",
          {
            params: { path: { definition_id: definition, value_id: id } },
            body,
          },
        ),
      );
    },
  };
}
