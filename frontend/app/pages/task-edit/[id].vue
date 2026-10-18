<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { productionApi } from "~/features/production/api";
import TaskEditor from "~/features/production-editor/TaskEditor.vue";
import DependenciesEditor from "~/features/production-editor/DependenciesEditor.vue";
import { provideDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
definePageMeta({ key: (route) => route.path });
provideDraftGuard("Hay cambios de planificación sin guardar. ¿Salir?");
const id = String(useRoute().params.id),
  api = productionApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: ["production-task", id],
  queryFn: () => api.task(id),
  retry: false,
});
async function refresh() {
  return !(await query.refetch()).isError;
}
useHead({ title: "Editar tarea · RRII-Coach" });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <NuxtLink :to="`/production/tasks/${id}`">Volver a la tarea</NuxtLink>
    <h1>Editar planificación</h1>
    <p v-if="query.isPending.value" role="status">Cargando…</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <UButton @click="refresh">Consultar registros actuales</UButton>
    <template v-if="query.data.value">
      <details class="asset-panel">
        <summary>Planificación guardada</summary>
        <p>{{ query.data.value.title }} · {{ query.data.value.status }}</p>
        <p>
          {{ query.data.value.planned_quantity }}
          {{ query.data.value.planned_unit }} ·
          {{ query.data.value.priority }} · Cola
          {{ query.data.value.queue_position }}
        </p>
        <p>{{ query.data.value.description }}</p>
        <p>{{ query.data.value.notes }}</p>
        <p>Máquina: {{ query.data.value.machine_id ?? "Sin máquina" }}</p>
        <pre style="white-space: pre-wrap; overflow-wrap: anywhere">{{
          JSON.stringify(query.data.value.production_parameters, null, 2)
        }}</pre>
      </details>
      <TaskEditor
        :task="query.data.value"
        :refresh="refresh"
      /><DependenciesEditor :task="query.data.value" :refresh="refresh" />
    </template>
  </div>
</template>
