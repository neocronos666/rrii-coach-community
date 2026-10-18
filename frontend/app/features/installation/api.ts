import createClient from "openapi-fetch";
import type { components, paths } from "~/types/api.generated";
import { ApiError, errorMessage } from "../shared/http";
export type Settings = components["schemas"]["InstallationSettings"];
export type SettingsUpdate =
  components["schemas"]["InstallationSettingsUpdate"];
function result<T>(response: {
  data?: T;
  error?: unknown;
  response: Response;
}): T {
  if (response.data === undefined)
    throw new ApiError(errorMessage(response.error), response.response.status);
  return response.data;
}
export function installationApi(base: string) {
  const client = createClient<paths>({
    baseUrl: base.replace(/\/$/, "").replace(/\/api\/v1$/, ""),
  });
  return {
    async get() {
      return result(await client.GET("/api/v1/settings"));
    },
    async save(body: SettingsUpdate) {
      return result(await client.PUT("/api/v1/settings", { body }));
    },
  };
}
