import { defineConfig } from "@playwright/test";

const apiBase = process.env.RRII_E2E_API_BASE?.replace(/\/$/, "");
if (!apiBase) {
  throw new Error(
    "Falta RRII_E2E_API_BASE. Los E2E requieren API, PostgreSQL y archivos aislados; no se omiten pruebas por falta de configuración.",
  );
}
const apiUrl = new URL(apiBase);
if (!["http:", "https:"].includes(apiUrl.protocol) || apiUrl.pathname !== "/api/v1") {
  throw new Error("RRII_E2E_API_BASE debe ser una URL HTTP(S) terminada en /api/v1.");
}
if (
  process.env.NUXT_PUBLIC_API_BASE_URL &&
  process.env.NUXT_PUBLIC_API_BASE_URL.replace(/\/$/, "") !== apiBase
) {
  throw new Error("La API del frontend y RRII_E2E_API_BASE deben coincidir.");
}
process.env.RRII_E2E_API_BASE = apiBase;

export default defineConfig({
  timeout: 60000,
  expect: { timeout: 15000 },
  testDir: "./tests/e2e",
  forbidOnly: true,
  workers: 1,
  retries: 0,
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      testIgnore: "**/touch-navigation.spec.ts",
    },
    {
      name: "chromium-touch",
      testMatch: "**/touch-navigation.spec.ts",
      use: {
        hasTouch: true,
        storageState: {
          cookies: [],
          origins: [
            {
              origin: "http://127.0.0.1:3100",
              localStorage: [
                {
                  name: "rrii-coach.device.v1",
                  value: JSON.stringify({
                    version: 1,
                    profile: "touch",
                    density: "comfortable",
                  }),
                },
              ],
            },
          ],
        },
      },
    },
  ],
  webServer: {
    command: process.env.PLAYWRIGHT_PREVIEW
      ? "NITRO_PORT=3100 node .output/server/index.mjs"
      : "pnpm exec nuxt dev --host 0.0.0.0 --port 3100",
    env: { NUXT_PUBLIC_API_BASE_URL: apiBase },
    url: "http://127.0.0.1:3100",
    reuseExistingServer: false,
    timeout: 120000,
  },
});
