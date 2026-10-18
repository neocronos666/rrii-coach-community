<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import MachineEditor from "~/features/machines/MachineEditor.vue";
import { machinesApi } from "~/features/machines/api";
import { machineTypes, optionalFields } from "~/features/machines/fields";
import { provideDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
definePageMeta({ key: (route) => route.path });
const id = String(useRoute().params.id),
  api = machinesApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: ["machine-detail", id],
  queryFn: () => api.get(id),
  retry: false,
});
provideDraftGuard("Hay cambios sin guardar. ¿Salir de la pantalla?");
async function refresh() {
  return !(await query.refetch()).isError;
}
useHead(() => ({
  title: `${query.data.value?.name ?? "Máquina"} · RRII-Coach`,
}));
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton to="/machines" color="neutral" variant="soft">Máquinas</UButton>
    <h1>{{ query.data.value?.name ?? "Máquina" }}</h1>
    <UButton color="neutral" variant="soft" @click="refresh"
      >Consultar registros actuales</UButton
    >
    <p v-if="query.isPending.value" role="status">Cargando máquina…</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <template v-if="query.data.value">
      <section class="asset-panel" aria-label="Datos guardados">
        <p>
          {{ machineTypes[query.data.value.machine_type] }} ·
          {{ query.data.value.active ? "Activa" : "Inactiva" }}
        </p>
        <dl>
          <template v-for="field in optionalFields" :key="field.key"
            ><dt>{{ field.label }}</dt>
            <dd>
              {{ query.data.value[field.key] ?? "Desconocido" }}
            </dd></template
          >
          <dt>Moneda</dt>
          <dd>{{ query.data.value.currency }}</dd>
          <dt>Notas</dt>
          <dd>{{ query.data.value.notes || "Sin notas" }}</dd>
        </dl>
      </section>
      <UButton :to="`/production?machine=${id}`" color="neutral" variant="soft"
        >Ver producción de esta máquina</UButton
      >
      <MachineEditor
        :machine="query.data.value"
        :refresh="refresh"
        @saved="refresh"
      />
    </template>
  </div>
</template>
