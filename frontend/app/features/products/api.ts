import createClient from "openapi-fetch";
import type { components, paths } from "~/types/api.generated";
import { allPages, unwrap } from "../shared/http";
export type Schema = components["schemas"];
export type Step = Schema["StepCreate"];
export type Configuration = Schema["ProductConfigurationInput"];
export type Selection = Schema["OptionSelection-Input"];
export function productApi(base: string) {
  const client = createClient<paths>({
    baseUrl: base.replace(/\/$/, "").replace(/\/api\/v1$/, ""),
  });
  return {
    async list(search: string, active: boolean, offset: number) {
      return unwrap(
        await client.GET("/api/v1/products", {
          params: {
            query: { search: search || undefined, active, offset, limit: 25 },
          },
        }),
      );
    },
    async products() {
      return allPages(async (offset) =>
        unwrap(
          await client.GET("/api/v1/products", {
            params: { query: { offset, limit: 100 } },
          }),
        ),
      );
    },
    async get(id: string) {
      return unwrap(
        await client.GET("/api/v1/products/{product_id}", {
          params: { path: { product_id: id } },
        }),
      );
    },
    async create(body: Schema["ProductCreate"]) {
      return unwrap(await client.POST("/api/v1/products", { body }));
    },
    async update(id: string, body: Schema["ProductUpdate"]) {
      return unwrap(
        await client.PATCH("/api/v1/products/{product_id}", {
          params: { path: { product_id: id } },
          body,
        }),
      );
    },
    async variants(id: string) {
      return allPages(async (offset) =>
        unwrap(
          await client.GET("/api/v1/products/{product_id}/variants", {
            params: { path: { product_id: id }, query: { offset, limit: 100 } },
          }),
        ),
      );
    },
    async variant(id: string) {
      return unwrap(
        await client.GET("/api/v1/product-variants/{variant_id}", {
          params: { path: { variant_id: id } },
        }),
      );
    },
    async addVariant(id: string, body: Schema["VariantCreate"]) {
      return unwrap(
        await client.POST("/api/v1/products/{product_id}/variants", {
          params: { path: { product_id: id } },
          body,
        }),
      );
    },
    async updateVariant(id: string, body: Schema["VariantUpdate"]) {
      return unwrap(
        await client.PATCH("/api/v1/product-variants/{variant_id}", {
          params: { path: { variant_id: id } },
          body,
        }),
      );
    },
    async configuration(id: string) {
      return unwrap(
        await client.GET("/api/v1/products/{product_id}/configuration", {
          params: { path: { product_id: id } },
        }),
      );
    },
    async saveConfiguration(id: string, body: Configuration) {
      return unwrap(
        await client.PUT("/api/v1/products/{product_id}/configuration", {
          params: { path: { product_id: id } },
          body,
        }),
      );
    },
    async definitions() {
      return allPages(async (offset) =>
        unwrap(
          await client.GET("/api/v1/option-definitions", {
            params: { query: { offset, limit: 100 } },
          }),
        ),
      );
    },
    async createDefinition(body: Schema["OptionDefinitionCreate"]) {
      return unwrap(await client.POST("/api/v1/option-definitions", { body }));
    },
    async values(id: string) {
      return allPages(async (offset) =>
        unwrap(
          await client.GET(
            "/api/v1/option-definitions/{definition_id}/values",
            {
              params: {
                path: { definition_id: id },
                query: { offset, limit: 100 },
              },
            },
          ),
        ),
      );
    },
    async createValue(id: string, body: Schema["OptionValueCreate"]) {
      return unwrap(
        await client.POST("/api/v1/option-definitions/{definition_id}/values", {
          params: { path: { definition_id: id } },
          body,
        }),
      );
    },
    async baseRecipe(id: string) {
      const result = await client.GET("/api/v1/products/{product_id}/recipe", {
        params: { path: { product_id: id } },
      });
      if (result.response.status === 404) return null;
      return unwrap(result);
    },
    async createRecipe(id: string, body: Schema["RecipeCreate"]) {
      return unwrap(
        await client.POST("/api/v1/products/{product_id}/recipe", {
          params: { path: { product_id: id } },
          body,
        }),
      );
    },
    async updateRecipe(id: string, body: Schema["RecipeCreate"]) {
      return unwrap(
        await client.PUT("/api/v1/recipes/{recipe_id}", {
          params: { path: { recipe_id: id } },
          body,
        }),
      );
    },
    async plan(id: string) {
      return unwrap(
        await client.GET("/api/v1/recipes/{recipe_id}/plan", {
          params: { path: { recipe_id: id } },
        }),
      );
    },
    async savePlan(id: string, body: Schema["RecipePlan"]) {
      return unwrap(
        await client.PUT("/api/v1/recipes/{recipe_id}/plan", {
          params: { path: { recipe_id: id } },
          body,
        }),
      );
    },
    async resolve(id: string, body: Schema["RecipeResolveInput"]) {
      return unwrap(
        await client.POST("/api/v1/products/{product_id}/recipe/resolve", {
          params: { path: { product_id: id } },
          body,
        }),
      );
    },
    async services() {
      return allPages(async (offset) =>
        unwrap(
          await client.GET("/api/v1/service-definitions", {
            params: { query: { offset, limit: 100 } },
          }),
        ),
      );
    },
    async createService(body: Schema["ServiceDefinitionCreate"]) {
      return unwrap(await client.POST("/api/v1/service-definitions", { body }));
    },
    async supplies() {
      return unwrap(await client.GET("/api/v1/supplies"));
    },
    async families() {
      return allPages(async (offset) =>
        unwrap(
          await client.GET("/api/v1/asset-families", {
            params: { query: { offset, limit: 100 } },
          }),
        ),
      );
    },
    async assets() {
      return allPages(async (offset) =>
        unwrap(
          await client.GET("/api/v1/assets", {
            params: { query: { offset, limit: 100 } },
          }),
        ),
      );
    },
    async revisions(id: string) {
      return allPages(async (offset) =>
        unwrap(
          await client.GET("/api/v1/assets/{asset_id}/revisions", {
            params: { path: { asset_id: id }, query: { offset, limit: 100 } },
          }),
        ),
      );
    },
  };
}
export type ProductApi = ReturnType<typeof productApi>;
