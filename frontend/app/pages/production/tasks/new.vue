<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import TaskEditor from "~/features/production-editor/TaskEditor.vue";
import { commercialApi } from "~/features/commercial/api";
import { productionApi, type Destination } from "~/features/production/api";
import { provideDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
definePageMeta({ key: (route) => route.fullPath });
provideDraftGuard("Hay cambios de planificación sin guardar. ¿Salir?");
const route = useRoute(),
  base = useRuntimeConfig().public.apiBaseUrl,
  commercial = commercialApi(base),
  production = productionApi(base);
const order = typeof route.query.order === "string" ? route.query.order : "",
  project = typeof route.query.project === "string" ? route.query.project : "",
  component =
    typeof route.query.component === "string" ? route.query.component : "";
const destination: Destination | null =
  order && !project && !component
    ? { kind: "order", id: order }
    : !order && project && component
      ? { kind: "component", id: component }
      : null;
const origin = useQuery({
  queryKey: ["manual-task-origin", order, project, component],
  enabled: !!destination,
  retry: false,
  queryFn: async () => {
    if (order) {
      const row = await commercial.order(order);
      return {
        title: `${row.code} · ${row.title}`,
        status: row.status,
        url: `/orders/${row.id}`,
      };
    }
    const row = await commercial.project(project);
    const child = row.components.find((c) => c.id === component);
    if (!child) throw new Error("El componente no pertenece al proyecto.");
    return {
      title: `${row.code} · ${child.description}`,
      status: row.status,
      url: `/projects/${row.id}`,
    };
  },
});
const tasks = useQuery({
  queryKey: ["manual-origin-tasks", order, component],
  enabled: !!destination,
  retry: false,
  queryFn: () =>
    production.tasks(
      order ? { order_id: order } : { project_component_id: component },
    ),
});
async function refresh() {
  const results = await Promise.all([origin.refetch(), tasks.refetch()]);
  return results.every((r) => !r.isError);
}
useHead({ title: "Crear tarea manual · RRII-Coach" });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <NuxtLink to="/production">Producción</NuxtLink>
    <h1>Crear tarea manual</h1>
    <p v-if="!destination" role="alert">
      Abrí esta pantalla desde un pedido o un componente de proyecto.
    </p>
    <p v-if="origin.isPending.value && destination" role="status">
      Cargando origen…
    </p>
    <p v-if="origin.error.value" role="alert">
      {{ errorMessage(origin.error.value) }}
    </p>
    <UButton v-if="destination" @click="refresh"
      >Consultar registros actuales</UButton
    >
    <template v-if="origin.data.value"
      ><NuxtLink :to="origin.data.value.url">{{
        origin.data.value.title
      }}</NuxtLink>
      <p v-if="origin.data.value.status !== 'pending'">
        El origen está cancelado.
      </p>
      <TaskEditor
        v-if="destination && origin.data.value.status === 'pending'"
        :destination="destination"
        :refresh="refresh"
    /></template>
    <section class="asset-panel">
      <h2>Tareas guardadas del origen</h2>
      <p v-if="tasks.error.value" role="alert">
        {{ errorMessage(tasks.error.value) }}
      </p>
      <ul>
        <li v-for="task in tasks.data.value" :key="task.id">
          <NuxtLink :to="`/production/tasks/${task.id}`"
            >{{ task.code }} · {{ task.title }}</NuxtLink
          >
        </li>
      </ul>
    </section>
  </div>
</template>
