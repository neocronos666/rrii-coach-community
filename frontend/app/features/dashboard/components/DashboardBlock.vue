<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import type { BlockId } from "../blocks";
import { dashboardApi } from "../data";
import { errorMessage } from "../../shared/http";
const props = withDefaults(
  defineProps<{ id: BlockId; view?: "list" | "summary" }>(),
  { view: "list" },
);
const api = dashboardApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: computed(() => ["dashboard-live", props.id]),
  queryFn: () => api.load(props.id),
  retry: false,
});
const destinations: Record<BlockId, string> = {
  production: "/production",
  quotes: "/quotes",
  attention: "/production",
  activity: "/quotes",
  machines: "/machines",
};
const descriptions: Record<BlockId, string> = {
  production: "Tareas en cola, en curso o pausadas.",
  quotes: "Presupuestos en borrador.",
  attention:
    "Tareas pausadas y presupuestos vencidos. No incluye alertas de stock.",
  activity:
    "Última actualización guardada de tareas y presupuestos; no es un historial de eventos.",
  machines: "Estado administrativo. Una máquina activa puede estar ocupada.",
};
const summary = computed(() =>
  Object.entries(
    (query.data.value ?? []).reduce<Record<string, number>>((result, row) => {
      result[row.status] = (result[row.status] ?? 0) + 1;
      return result;
    }, {}),
  ),
);
</script>
<template>
  <div class="asset-form dashboard-live">
    <p>{{ descriptions[id] }}</p>
    <p v-if="query.isPending.value" role="status">Consultando registros…</p>
    <div v-if="query.error.value" role="alert">
      <p>{{ errorMessage(query.error.value) }}</p>
      <p>
        No se pudo actualizar este bloque. No se interpreta como ausencia de
        registros.
      </p>
    </div>
    <template v-if="query.data.value">
      <p v-if="query.error.value">Se conserva la última consulta correcta.</p>
      <p data-testid="dashboard-count">
        {{ query.data.value.length }} registros
      </p>
      <p v-if="!query.data.value.length">No hay registros para este bloque.</p>
      <ul v-else-if="view === 'summary'" data-testid="dashboard-summary">
        <li v-for="[status, count] in summary" :key="status">
          {{ status }}: {{ count }}
        </li>
      </ul>
      <ul v-else class="asset-form">
        <li v-for="row in query.data.value.slice(0, 8)" :key="row.id">
          <NuxtLink :to="row.to">{{ row.title }}</NuxtLink>
          <p>
            {{ row.status }}<span v-if="row.amount"> · {{ row.amount }}</span>
          </p>
          <time :datetime="row.updated">{{
            new Date(row.updated).toLocaleString("es-AR")
          }}</time>
        </li>
      </ul>
      <p v-if="view === 'list' && query.data.value.length > 8">
        Se muestran los primeros 8 registros.
      </p>
      <p class="preference-note">
        Consultado:
        {{ new Date(query.dataUpdatedAt.value).toLocaleTimeString("es-AR") }}
      </p>
    </template>
    <div class="asset-actions">
      <UButton
        color="neutral"
        variant="soft"
        :disabled="query.isFetching.value"
        @click="query.refetch()"
        >Actualizar bloque</UButton
      ><NuxtLink :to="destinations[id]">Abrir sección</NuxtLink>
    </div>
  </div>
</template>
