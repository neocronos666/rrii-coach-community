import createClient from "openapi-fetch";
import type { components, paths } from "~/types/api.generated";
import { ApiError, errorMessage } from "../shared/http";
export type Schema = components["schemas"];
function result<T>(r: { data?: T; error?: unknown; response: Response }): T {
  if (r.data === undefined)
    throw new ApiError(errorMessage(r.error), r.response.status);
  return r.data;
}
export function compositionApi(base: string) {
  const client = createClient<paths>({
    baseUrl: base.replace(/\/$/, "").replace(/\/api\/v1$/, ""),
  });
  return {
    async calculation(id: string) {
      return result(
        await client.GET("/api/v1/cost-calculations/{calculation_id}", {
          params: { path: { calculation_id: id } },
        }),
      );
    },
    async calculate(body: Schema["CostCalculationRequest"]) {
      return result(await client.POST("/api/v1/cost-calculations", { body }));
    },
    async create(body: Schema["QuoteCreate"]) {
      return result(await client.POST("/api/v1/quotes", { body }));
    },
    async update(id: string, items: Schema["QuoteItemInput"][]) {
      return result(
        await client.PATCH("/api/v1/quotes/{quote_id}", {
          params: { path: { quote_id: id } },
          body: { items },
        }),
      );
    },
  };
}
