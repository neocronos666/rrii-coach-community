import createClient from "openapi-fetch";
import type { components, paths } from "~/types/api.generated";
import { errorMessage, allPages } from "../shared/http";
export type Schema = components["schemas"];
export type Definition = Omit<Schema["QuickQuoteCreate"], "request_id">;
export type Pricing = Schema["PricingPreviewCreate-Input"];
import { ApiError as QuoteApiError } from "../shared/http";
export { ApiError as QuoteApiError } from "../shared/http";
function result<T>(response: {
  data?: T;
  error?: unknown;
  response: Response;
}): T {
  if (response.data === undefined)
    throw new QuoteApiError(
      errorMessage(response.error),
      response.response.status,
    );
  return response.data;
}
export function quickQuoteApi(base: string) {
  const client = createClient<paths>({
    baseUrl: base.replace(/\/$/, "").replace(/\/api\/v1$/, ""),
  });
  return {
    async list(offset: number) {
      return result(
        await client.GET("/api/v1/quick-quotes", {
          params: { query: { offset, limit: 25 } },
        }),
      );
    },
    async get(id: string) {
      return result(
        await client.GET("/api/v1/quick-quotes/{quote_id}", {
          params: { path: { quote_id: id } },
        }),
      );
    },
    async history(id: string) {
      return allPages(async (offset) =>
        result(
          await client.GET("/api/v1/quick-quotes/{quote_id}/revisions", {
            params: { path: { quote_id: id }, query: { offset, limit: 100 } },
          }),
        ),
      );
    },
    async preview(body: Pricing) {
      return result(await client.POST("/api/v1/pricing-preview", { body }));
    },
    async create(body: Schema["QuickQuoteCreate"]) {
      return result(await client.POST("/api/v1/quick-quotes", { body }));
    },
    async replace(id: string, body: Schema["QuickQuoteReplace"]) {
      return result(
        await client.PUT("/api/v1/quick-quotes/{quote_id}", {
          params: { path: { quote_id: id } },
          body,
        }),
      );
    },
    async recalculate(id: string, body: Schema["QuickQuoteRecalculate"]) {
      return result(
        await client.POST("/api/v1/quick-quotes/{quote_id}/recalculate", {
          params: { path: { quote_id: id } },
          body,
        }),
      );
    },
    async formalize(id: string, body: Schema["QuickQuoteFormalize"]) {
      return result(
        await client.POST("/api/v1/quick-quotes/{quote_id}/formalize", {
          params: { path: { quote_id: id } },
          body,
        }),
      );
    },
    async formalization(id: string) {
      const response = await client.GET(
        "/api/v1/quick-quotes/{quote_id}/formalization",
        { params: { path: { quote_id: id } } },
      );
      if (response.response.status === 404) return null;
      return result(response);
    },
    async quote(id: string) {
      return result(
        await client.GET("/api/v1/quotes/{quote_id}", {
          params: { path: { quote_id: id } },
        }),
      );
    },
    async quotes() {
      return result(await client.GET("/api/v1/quotes"));
    },
    async recipes(variant: string) {
      return result(
        await client.GET("/api/v1/product-variants/{variant_id}/recipes", {
          params: { path: { variant_id: variant } },
        }),
      );
    },
    async machines() {
      return result(await client.GET("/api/v1/machines"));
    },
  };
}
export type QuickQuoteApi = ReturnType<typeof quickQuoteApi>;
export function newDefinition(): Definition {
  return {
    title: "",
    notes: null,
    pricing: {
      recipe_id: "",
      variant_id: "",
      target_quantity: "1",
      strategy: "fifo",
      markup_percentage: null,
      selections: [],
      step_estimates: {},
    },
  };
}
