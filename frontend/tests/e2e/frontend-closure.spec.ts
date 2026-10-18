import { expect, test } from "@playwright/test";
const api = process.env.RRII_E2E_API_BASE!;
test("cierre: enlaces principales cargan pantallas reales sin errores de ejecución", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const ready = await request.get(`${api!.replace(/\/api\/v1$/, "")}/ready`);
  expect(ready.status()).toBe(200);
  expect((await ready.json()).schema_status).toBe("current");
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  for (const route of [
    "/",
    "/quotes",
    "/production",
    "/products",
    "/assets",
    "/inventory",
  ]) {
    await page.goto(route);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(
      page.getByText("Este espacio está en camino", { exact: true }),
    ).toHaveCount(0);
    expect(await page.locator("h1").innerText(), route).not.toBe("");
  }
  expect(errors).toEqual([]);
});
