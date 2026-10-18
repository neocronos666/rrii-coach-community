import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchBackendHealth } from "../../app/utils/health";

describe("fetchBackendHealth", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("valida una respuesta saludable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            status: "ok",
            service: "rrii-coach-backend",
          }),
          { status: 200 },
        ),
      ),
    );

    await expect(
      fetchBackendHealth("http://localhost:8000/api/v1"),
    ).resolves.toEqual({
      status: "ok",
      service: "rrii-coach-backend",
    });
  });
});
