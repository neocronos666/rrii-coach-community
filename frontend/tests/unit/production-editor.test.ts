import { afterEach, expect, test, vi } from "vitest";
import { taskEditorApi } from "../../app/features/production-editor/api";
import {
  taskDraft,
  taskChanges,
  parameters,
} from "../../app/features/production-editor/fields";
afterEach(() => vi.unstubAllGlobals());
test("PATCH sólo diferencias y conserva precisión, null y parámetros", () => {
  const original = taskDraft();
  expect(
    taskChanges(
      { ...original, planned_quantity: "1.000001", notes: "Real" },
      original,
    ),
  ).toEqual({ planned_quantity: "1.000001", notes: "Real" });
  expect(
    taskChanges(
      { ...original, description: "" },
      { ...original, description: "Anterior" },
    ),
  ).toEqual({ description: null });
  expect(() => parameters("[]")).toThrow("objeto JSON");
  expect(() => parameters("{")).toThrow();
  expect(parameters('{"temperature":200}')).toEqual({ temperature: 200 });
});
test("alta parent-scoped y DELETE elimina solamente la dependencia con 204", async () => {
  const requests: Request[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    requests.push(request);
    return request.method === "DELETE"
      ? new Response(null, { status: 204 })
      : new Response("{}");
  });
  const api = taskEditorApi("http://api.test/api/v1");
  const body = {
    title: "Tarea",
    task_type: "manual" as const,
    planned_quantity: "2.123456",
    priority: "normal" as const,
    queue_position: 0,
  };
  await api.create({ kind: "order", id: "order" }, body);
  await api.create({ kind: "component", id: "component" }, body);
  await api.removeDependency("task", "previous");
  expect(requests.map((r) => new URL(r.url).pathname)).toEqual([
    "/api/v1/orders/order/production-tasks",
    "/api/v1/project-components/component/production-tasks",
    "/api/v1/production-tasks/task/dependencies/previous",
  ]);
  expect(await requests[0]!.json()).toEqual(body);
});

test("opciones de intento distinguen herencia de override vacío y convierten UTC", async () => {
  const { startPayload } = await import(
    "../../app/features/production-editor/run-options"
  );
  expect(
    startPayload("", { startedAt: "", override: false, parameters: "invalid" }),
  ).toEqual({});
  expect(
    startPayload("none", {
      startedAt: "2026-10-15T10:00:00-03:00",
      override: true,
      parameters: "{}",
    }),
  ).toEqual({
    machine_id: null,
    started_at: "2026-10-15T13:00:00.000Z",
    parameters: {},
  });
});
