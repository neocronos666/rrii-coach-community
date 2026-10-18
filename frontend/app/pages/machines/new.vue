<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import MachineEditor from "~/features/machines/MachineEditor.vue";
import { machinesApi } from "~/features/machines/api";
import { provideDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
const api = machinesApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: ["machines-review"],
  queryFn: () => api.list(),
  retry: false,
});
provideDraftGuard("Hay cambios sin guardar. ¿Salir de la pantalla?");
async function refresh() {
  return !(await query.refetch()).isError;
}
useHead({ title: "Registrar máquina · RRII-Coach" });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton to="/machines" color="neutral" variant="soft">Máquinas</UButton>
    <h1>Registrar máquina</h1>
    <MachineEditor
      :refresh="refresh"
      @saved="(id) => navigateTo(`/machines/${id}`)"
    />
    <section class="asset-panel">
      <h2>Registros actuales para revisar el resultado</h2>
      <p v-if="query.error.value" role="alert">
        {{ errorMessage(query.error.value) }}
      </p>
      <ul>
        <li v-for="row in query.data.value" :key="row.id">
          <NuxtLink :to="`/machines/${row.id}`">{{ row.name }}</NuxtLink> ·
          {{ row.id }}
        </li>
      </ul>
    </section>
  </div>
</template>
