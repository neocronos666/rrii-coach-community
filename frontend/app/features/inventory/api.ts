import createClient from "openapi-fetch";
import type { components, paths } from "~/types/api.generated";
import { ApiError, errorMessage, allPages } from "../shared/http";
export type Schema = components["schemas"];
function result<T>(r: { data?: T; error?: unknown; response: Response }): T {
  if (r.data === undefined)
    throw new ApiError(errorMessage(r.error), r.response.status);
  return r.data;
}
export function inventoryApi(base: string) {
  const client = createClient<paths>({
    baseUrl: base.replace(/\/$/, "").replace(/\/api\/v1$/, ""),
  });
  return {
    async supplies(active?: boolean, category?: Schema["SupplyCategory"]) {
      return result(
        await client.GET("/api/v1/supplies", {
          params: { query: { active, category } },
        }),
      );
    },
    async supply(id: string) {
      return result(
        await client.GET("/api/v1/supplies/{supply_id}", {
          params: { path: { supply_id: id } },
        }),
      );
    },
    async createSupply(body: Schema["SupplyCreate"]) {
      return result(await client.POST("/api/v1/supplies", { body }));
    },
    async updateSupply(id: string, body: Schema["SupplyUpdate"]) {
      return result(
        await client.PATCH("/api/v1/supplies/{supply_id}", {
          params: { path: { supply_id: id } },
          body,
        }),
      );
    },
    async presentations(id: string) {
      return result(
        await client.GET("/api/v1/supplies/{supply_id}/presentations", {
          params: { path: { supply_id: id } },
        }),
      );
    },
    async addPresentation(id: string, body: Schema["PresentationCreate"]) {
      return result(
        await client.POST("/api/v1/supplies/{supply_id}/presentations", {
          params: { path: { supply_id: id } },
          body,
        }),
      );
    },
    async purchases(id: string) {
      return result(
        await client.GET("/api/v1/supplies/{supply_id}/purchases", {
          params: { path: { supply_id: id } },
        }),
      );
    },
    async purchase(id: string, body: Schema["PurchaseCreate"]) {
      return result(
        await client.POST("/api/v1/supplies/{supply_id}/purchases", {
          params: { path: { supply_id: id } },
          body,
        }),
      );
    },
    async adjust(id: string, body: Schema["AdjustmentCreate"]) {
      return result(
        await client.POST("/api/v1/supplies/{supply_id}/adjustments", {
          params: { path: { supply_id: id } },
          body,
        }),
      );
    },
    async movements(id: string) {
      return result(
        await client.GET("/api/v1/supplies/{supply_id}/movements", {
          params: { path: { supply_id: id } },
        }),
      );
    },
    async availability(id: string) {
      return result(
        await client.GET("/api/v1/supplies/{supply_id}/availability", {
          params: { path: { supply_id: id } },
        }),
      );
    },
    async cost(id: string) {
      const response = await client.GET(
        "/api/v1/supplies/{supply_id}/estimated-cost",
        { params: { path: { supply_id: id } } },
      );
      if (response.response.status === 404) return null;
      return result(response);
    },
    async reservations(id: string) {
      return result(
        await client.GET(
          "/api/v1/production-tasks/{task_id}/supply-reservations",
          { params: { path: { task_id: id } } },
        ),
      );
    },
    async reserve(
      task: string,
      supply: string,
      body: Schema["ReservationSet"],
    ) {
      return result(
        await client.PUT(
          "/api/v1/production-tasks/{task_id}/supply-reservations/{supply_id}",
          { params: { path: { task_id: task, supply_id: supply } }, body },
        ),
      );
    },
    async stock(id: string) {
      return result(
        await client.GET("/api/v1/product-variants/{variant_id}/stock", {
          params: { path: { variant_id: id } },
        }),
      );
    },
    async stockMovements(id: string) {
      return allPages(async (offset) =>
        result(
          await client.GET(
            "/api/v1/product-variants/{variant_id}/stock-movements",
            {
              params: {
                path: { variant_id: id },
                query: { offset, limit: 100 },
              },
            },
          ),
        ),
      );
    },
    async move(id: string, body: Schema["StockMovementCreate"]) {
      return result(
        await client.POST(
          "/api/v1/product-variants/{variant_id}/stock-movements",
          { params: { path: { variant_id: id } }, body },
        ),
      );
    },
    async allocations(order?: string, component?: string) {
      return allPages(async (offset) =>
        result(
          await client.GET("/api/v1/product-allocations", {
            params: {
              query: {
                order_id: order,
                project_component_id: component,
                offset,
                limit: 100,
              },
            },
          }),
        ),
      );
    },
    async allocate(body: Schema["AllocationCreate"]) {
      return result(await client.POST("/api/v1/product-allocations", { body }));
    },
    async allocation(id: string) {
      return result(
        await client.GET("/api/v1/product-allocations/{allocation_id}", {
          params: { path: { allocation_id: id } },
        }),
      );
    },
    async release(id: string) {
      return result(
        await client.POST(
          "/api/v1/product-allocations/{allocation_id}/release",
          { params: { path: { allocation_id: id } } },
        ),
      );
    },
    async deliver(id: string, body: Schema["AllocationDelivery"]) {
      return result(
        await client.POST(
          "/api/v1/product-allocations/{allocation_id}/deliver",
          { params: { path: { allocation_id: id } }, body },
        ),
      );
    },
  };
}
