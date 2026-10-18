import { useQuery } from "@tanstack/vue-query";
import type { ProductApi } from "./api";
export async function loadCatalog(api: ProductApi) {
  const [definitions, services, supplies, families, assets, products] =
    await Promise.all([
      api.definitions(),
      api.services(),
      api.supplies(),
      api.families(),
      api.assets(),
      api.products(),
    ]);
  const values = (
    await Promise.all(definitions.map((row) => api.values(row.id)))
  ).flat();
  return {
    definitions,
    values,
    services,
    supplies,
    families,
    assets,
    products,
  };
}
export type Catalog = Awaited<ReturnType<typeof loadCatalog>>;
export function useCatalog(api: ProductApi) {
  return useQuery({
    queryKey: ["product-editor-catalog"],
    queryFn: () => loadCatalog(api),
    retry: false,
  });
}
