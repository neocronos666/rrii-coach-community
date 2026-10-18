<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { taskEditorApi, type Schema } from "./api";
import { productionApi } from "../production/api";
import { commercialApi } from "../commercial/api";
import { useRecordedWrite } from "../inventory/useRecordedWrite";
import WriteStatus from "../inventory/WriteStatus.vue";
import { useDraftGuard } from "../shared/useDraftGuard";
import { errorMessage } from "../shared/http";
const props = defineProps<{
  task: Schema["ProductionTaskRead"];
  refresh: () => Promise<boolean>;
}>();
const base = useRuntimeConfig().public.apiBaseUrl,
  api = taskEditorApi(base),
  production = productionApi(base);
const query = useQuery({
  queryKey: ["task-edit-dependencies", props.task.id],
  queryFn: async () => {
    let siblings: Schema["ProductionTaskRead"][];
    if (props.task.order_id)
      siblings = await production.tasks({ order_id: props.task.order_id });
    else {
      const projects = await commercialApi(base).projects();
      const parent = projects.find((p) =>
        p.components.some((c) => c.id === props.task.project_component_id),
      );
      if (!parent)
        throw new Error("No se pudo resolver el proyecto de la tarea.");
      siblings = await production.tasks({ project_id: parent.id });
    }
    return {
      dependencies: await production.dependencies(props.task.id),
      siblings,
    };
  },
  retry: false,
});
const selected = ref("");
const markSaved = useDraftGuard("task-dependency", () => selected.value);
async function refresh() {
  const results = await Promise.all([query.refetch(), props.refresh()]);
  return !results[0].isError && results[1];
}
const state = useRecordedWrite(`task-dependencies:${props.task.id}`, refresh);
const editable = computed(
  () => props.task.status === "queued" && props.task.origin !== "recipe",
);
async function add() {
  if (!selected.value || !editable.value) return;
  const row = await state.run("Agregar prerrequisito", () =>
    api.addDependency(props.task.id, selected.value),
  );
  if (row) {
    selected.value = "";
    markSaved();
  }
}
async function remove(id: string) {
  if (
    !editable.value ||
    !window.confirm(
      "¿Retirar este prerrequisito de la planificación? No se elimina la tarea.",
    )
  )
    return;
  await state.run("Retirar prerrequisito", () =>
    api.removeDependency(props.task.id, id),
  );
}
</script>
<template>
  <section class="asset-panel asset-form">
    <h2>Dependencias de planificación</h2>
    <WriteStatus :state="state" />
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <UButton @click="refresh">Actualizar dependencias</UButton>
    <ul>
      <li
        v-for="row in query.data.value?.dependencies"
        :key="row.depends_on_task_id"
      >
        <NuxtLink :to="`/production/tasks/${row.depends_on_task_id}`"
          >{{ row.prerequisite.code }} · {{ row.prerequisite.title }}</NuxtLink
        >
        <UButton
          v-if="editable"
          :disabled="state.locked.value"
          @click="remove(row.depends_on_task_id)"
          >Retirar {{ row.prerequisite.title }}</UButton
        >
      </li>
    </ul>
    <p v-if="!editable">
      Las dependencias de recetas y de tareas que ya comenzaron son inmutables.
    </p>
    <form v-else @submit.prevent="add">
      <fieldset :disabled="state.locked.value || !query.data.value">
        <label
          >Prerrequisito<select v-model="selected" required>
            <option value="">Elegir tarea del mismo origen</option>
            <option
              v-for="row in query.data.value?.siblings.filter(
                (row) => row.id !== task.id,
              )"
              :key="row.id"
              :value="row.id"
            >
              {{ row.code }} · {{ row.title }}
            </option>
          </select></label
        ><UButton type="submit">Agregar prerrequisito</UButton>
      </fieldset>
    </form>
  </section>
</template>
